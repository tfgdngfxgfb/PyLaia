"""Exercise the actual SymPy/mpmath and W&B/cwevals contracts, offline."""

import asyncio
from importlib.metadata import distribution, version

import pytest
import sympy as sp
import torch
from mpmath import mp
from packaging.requirements import Requirement


def test_local_sympy_metadata_matches_numeric_backend():
    assert sp.__version__ == version("sympy") == "1.14.0+pylaia1"
    assert version("mpmath") == "1.4.1"
    requirement = next(
        Requirement(r)
        for r in distribution("sympy").requires
        if Requirement(r).name == "mpmath"
    )
    assert str(requirement.specifier) == "==1.4.1"


def test_sympy_high_precision_lambdify_and_numeric_integration():
    x = sp.Symbol("x")
    assert sp.simplify(sp.sin(x) ** 2 + sp.cos(x) ** 2) == 1
    assert sp.integrate(sp.exp(-x), (x, 0, sp.oo)) == 1
    assert abs(
        sp.N(sp.Integral(sp.exp(-x * x), (x, 0, sp.oo)), 50)
        - sp.N(sp.sqrt(sp.pi) / 2, 50)
    ) < sp.Float("1e-48")
    function = sp.lambdify(x, sp.sin(x) + sp.besselj(0, x), "mpmath")
    with mp.workdps(60):
        value = mp.mpf("0.25")
        assert mp.almosteq(function(value), mp.sin(value) + mp.besselj(0, value))
        assert str(sp.N(sp.pi, 60)).startswith(
            "3.1415926535897932384626433832795028841971693993751"
        )


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_torch_symbolic_shapes_with_local_sympy(device):
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable on this runner")

    class Model(torch.nn.Module):
        def forward(self, inputs):
            return inputs.sin() + inputs.square()

    model = Model().to(device)
    inputs = torch.randn(3, 4, device=device)
    exported = torch.export.export(
        model, (inputs,), dynamic_shapes=({0: torch.export.Dim("batch", min=1, max=8)},)
    )
    different_batch = torch.randn(5, 4, device=device, requires_grad=True)
    actual = exported.module()(different_batch)
    expected = model(different_batch)
    torch.testing.assert_close(actual, expected)
    actual.sum().backward()
    torch.testing.assert_close(
        different_batch.grad,
        different_batch.detach().cos() + 2 * different_batch.detach(),
    )


def test_local_wandb_dependency_metadata():
    pytest.importorskip("wandb")
    assert version("wandb") == "0.31.0+pylaia1"
    assert version("cwevals") == "0.0.1b2"
    requirement = next(
        Requirement(r)
        for r in distribution("wandb").requires
        if Requirement(r).name == "cwevals"
    )
    assert str(requirement.specifier) == "==0.0.1b2"


@pytest.mark.parametrize("asynchronous", [False, True])
def test_cwevals_client_contract_without_network(asynchronous, monkeypatch):
    pytest.importorskip("wandb")
    import httpx
    from coreweave_evaluations import AsyncClient, Client

    for name in ("WANDB_ACCESS_TOKEN", "WANDB_API_KEY", "CES_CUSTOM_HEADERS"):
        monkeypatch.delenv(name, raising=False)
    requests = []

    def handler(request):
        assert request.method == "GET"
        assert request.url.host == "offline.invalid"
        requests.append(request)
        return httpx.Response(200, json={"message": "ok"})

    transport = httpx.MockTransport(handler)
    if asynchronous:

        async def exercise():
            async with AsyncClient(
                base_url="https://offline.invalid",
                api_key="offline-test",
                http_client=httpx.AsyncClient(transport=transport),
            ) as client:
                assert (await client.service.get()).message == "ok"

        asyncio.run(exercise())
    else:
        with Client(
            base_url="https://offline.invalid",
            api_key="offline-test",
            http_client=httpx.Client(transport=transport),
        ) as client:
            assert client.service.get().message == "ok"
    assert len(requests) == 1
