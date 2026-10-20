"""Quick offline verification of the installed PyLaia and native LM packages."""

import argparse
import runpy
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

import torch

from laia.common.loader import BasicLoader
from laia.decoders import CTCLanguageDecoder

if __package__:
    from .verify_torch_runtime import verify_autograd
else:
    verify_autograd = runpy.run_path(
        str(Path(__file__).with_name("verify_torch_runtime.py"))
    )["verify_autograd"]

TOKENS = "<ctc>\na\ne\nh\ni\ns\nt\n.\n<unk>\n<space>\n"
LEXICON = "\n".join(f"{token} {token}" for token in TOKENS.splitlines()) + "\n"
ARPA = r"""\data\
ngram 1=10
ngram 2=14

\1-grams:
-1.09691	.	-0.2648178
-1.09691	</s>
-99	<s>	-0.2253093
-0.79588	<space>	-0.10721
-1.09691	a	-0.2253093
-1.09691	e	-0.2253093
-1.09691	h	-0.2455126
-0.9208187	i	-0.4014006
-0.79588	s	-0.2304489
-0.79588	t	-0.1818436

\2-grams:
-0.30103	. </s>
-0.30103	<s> t
-0.7781513	<space> a
-0.7781513	<space> i
-0.7781513	<space> t
-0.30103	a <space>
-0.30103	e s
-0.30103	h i
-0.1760913	i s
-0.39794	s <space>
-0.69897	s t
-0.7781513	t .
-0.7781513	t e
-0.7781513	t h

\end\
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-cuda", action="store_true")
    parser.add_argument("--check-wandb", action="store_true")
    args = parser.parse_args()
    import sympy as sp

    assert sp.__version__ == version("sympy") == "1.14.0+pylaia1"
    assert version("mpmath") == "1.4.1"
    assert str(sp.N(sp.pi, 50)).startswith("3.1415926535897932384626433832795")
    x = sp.Symbol("x")
    assert sp.integrate(sp.exp(-x), (x, 0, sp.oo)) == 1
    if args.check_wandb:
        import wandb

        assert wandb.__version__ == version("wandb") == "0.31.0+pylaia1"
        assert version("cwevals") == "0.0.1b2"
        with tempfile.TemporaryDirectory(prefix="PyLaia-Wandb-æøå-") as directory:
            with wandb.init(
                project="pylaia-installation-check",
                mode="offline",
                dir=directory,
                settings=wandb.Settings(
                    disable_git=True, disable_code=True, console="off", silent=True
                ),
            ) as run:
                assert run.settings.mode == "offline"
                run.log({"installation_verified": 1})
    verify_autograd("cpu")
    if args.require_cuda and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA unavailable: check the NVIDIA driver or install the CPU variant"
        )
    if args.require_cuda:
        verify_autograd("cuda")
        assert (torch.ones(2, device="cuda") * 2).sum().item() == 4
        assert torch.backends.cudnn.enabled
        model = torch.nn.LSTM(16, 16, 2, bidirectional=True, dropout=0.5).cuda()
        inputs = torch.randn(4, 2, 16, device="cuda", requires_grad=True)
        model(inputs)[0].sum().backward()
        assert inputs.grad is not None
        assert model.dropout == 0.5 and torch.backends.cudnn.enabled
    features = torch.tensor(
        [
            [[-2.1, -1.3, -4.1, -4.2, -5.0, -5.1, -0.2, -4.2, -5.2, -1.2]],
            [[-2.1, -0.1, -0.3, -4.2, -5.0, -5.1, -4.7, -4.2, -5.2, -1.2]],
            [[-2.1, -2.5, -4.1, -4.2, -5.0, -0.7, -0.9, -1.7, -5.2, -1.2]],
            [[-2.1, -0.5, -4.1, -4.2, -5.0, -0.7, -0.1, -1.1, -5.2, -1.2]],
        ]
    )
    with tempfile.TemporaryDirectory(prefix="PyLaia-æøå-") as directory:
        path = Path(directory)
        (path / "tokens.txt").write_text(TOKENS, encoding="utf-8")
        (path / "lexicon.txt").write_text(LEXICON, encoding="utf-8")
        (path / "lm.arpa").write_text(ARPA, encoding="utf-8", newline="\n")
        for weight, expected in ((0, "tast"), (1, "test")):
            decoder = CTCLanguageDecoder(
                str(path / "lm.arpa"),
                str(path / "lexicon.txt"),
                str(path / "tokens.txt"),
                language_model_weight=weight,
            )
            hypothesis = decoder(features)["hyp"][0]
            actual = (
                "".join(TOKENS.splitlines()[token] for token in hypothesis)
                .replace("<space>", " ")
                .strip()
            )
            assert actual == expected, (actual, expected)
        torch.save({"weight": torch.arange(4)}, path / "weights.pt")
        assert torch.equal(
            BasicLoader().load(path / "weights.pt")["weight"], torch.arange(4)
        )
    print(
        f"Python {sys.version.split()[0]} / PyLaia {version('pylaia')} / PyTorch {torch.__version__}"
    )
    print(
        f"Flashlight {version('flashlight-text')} / KenLM {version('kenlm')}: decoding verified"
    )
    print(
        f"SymPy {version('sympy')} / mpmath {version('mpmath')}: numerical evaluation verified"
    )
    if args.check_wandb:
        print(
            f"W&B {version('wandb')} / cwevals {version('cwevals')}: offline logging verified"
        )


if __name__ == "__main__":
    main()
