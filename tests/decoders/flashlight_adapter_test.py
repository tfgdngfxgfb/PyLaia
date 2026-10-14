"""Native adapter parity and raw-pointer input validation."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch

from ci.verify_installation import ARPA, TOKENS
from laia.decoders._flashlight_ctc_decoder import _Decoder, ctc_decoder


@pytest.fixture
def decoder_args(tmp_path):
    pytest.importorskip("flashlight.lib.text.decoder")
    # Blank/silence are control tokens, not lexical words. Including silence
    # as a word creates tied word-boundary paths at lm_weight=0: even two
    # TorchAudio decoders can return different words for identical tokens/scores.
    lexicon = "".join(
        f"{token} {token}\n"
        for token in TOKENS.splitlines()
        if token not in {"<ctc>", "<space>"}
    )
    for filename, content in (
        ("lm.arpa", ARPA),
        ("tokens.txt", TOKENS),
        ("lexicon.txt", lexicon),
    ):
        (tmp_path / filename).write_text(content, encoding="utf-8", newline="\n")
    return dict(
        lm=str(tmp_path / "lm.arpa"),
        tokens=str(tmp_path / "tokens.txt"),
        lexicon=str(tmp_path / "lexicon.txt"),
        lm_weight=1.0,
        blank_token="<ctc>",
        sil_token="<space>",
        unk_word="<unk>",
    )


@pytest.mark.parametrize("use_lexicon", [False, True])
@pytest.mark.parametrize("lm_weight", [0.0, 1.0])
def test_native_adapter_matches_torchaudio(decoder_args, use_lexicon, lm_weight):
    audio = pytest.importorskip("torchaudio.models.decoder")
    args = dict(decoder_args, lm_weight=lm_weight)
    if not use_lexicon:
        args["lexicon"] = None
    generator = torch.Generator().manual_seed(315)
    emissions = torch.randn(2, 7, 10, generator=generator).log_softmax(-1).contiguous()
    lengths = torch.tensor([7, 4], dtype=torch.int32)
    reference = audio.ctc_decoder(**args)(emissions, lengths)
    actual = ctc_decoder(**args)(emissions, lengths)
    for expected_batch, actual_batch in zip(reference, actual):
        assert len(actual_batch) == len(expected_batch)
        for expected, hypothesis in zip(expected_batch, actual_batch):
            assert torch.equal(hypothesis.tokens, expected.tokens)
            assert hypothesis.words == expected.words
            assert torch.equal(hypothesis.timesteps, expected.timesteps)
            assert hypothesis.score == pytest.approx(expected.score, abs=1e-6)


@pytest.mark.parametrize("use_lexicon", [False, True])
def test_adapter_variable_lengths_and_repeated_calls(decoder_args, use_lexicon):
    args = dict(decoder_args)
    if not use_lexicon:
        args["lexicon"] = None
    decoder = ctc_decoder(**args)
    generator = torch.Generator().manual_seed(315)
    emissions = torch.randn(2, 7, 10, generator=generator).log_softmax(-1).contiguous()
    lengths = torch.tensor([7, 4], dtype=torch.int32)
    batched = decoder(emissions, lengths)
    for index, length in enumerate(lengths.tolist()):
        separate = decoder(emissions[index : index + 1, :length].contiguous())[0][0]
        assert torch.equal(batched[index][0].tokens, separate.tokens)
        assert batched[index][0].score == pytest.approx(separate.score)


@pytest.mark.parametrize(
    "emissions,lengths",
    [
        (torch.zeros(2, 4, 10, dtype=torch.float64), None),
        (torch.zeros(2, 4, 10, device="meta"), None),
        (torch.zeros(2, 10, 4).transpose(1, 2), None),
        (torch.zeros(4, 10), None),
        (torch.zeros(2, 4, 9), None),
        (torch.zeros(2, 4, 10), torch.tensor([4])),
        (torch.zeros(2, 4, 10), torch.tensor([4, -1])),
        (torch.zeros(2, 4, 10), torch.tensor([4, 5])),
        (torch.zeros(2, 4, 10), torch.tensor([4.0, 3.0])),
    ],
)
def test_invalid_input_never_reaches_native_pointer_api(emissions, lengths):
    native = Mock()
    dictionary = SimpleNamespace(index_size=lambda: 10)
    decoder = _Decoder(native, None, dictionary, None, blank=0)
    with pytest.raises((ValueError, RuntimeError)):
        decoder(emissions, lengths)
    native.decode.assert_not_called()
