"""TorchAudio-independent adapter for the Flashlight CTC API on Python 3.15.

Adapted from torchaudio 2.11.0, models/decoder/_ctc_decoder.py.
Copyright (c) 2017 Facebook Inc. (Soumith Chintala). BSD-2-Clause;
see the distributed LICENSE-TORCHAUDIO. Only PyLaia's offline decoding path
is implemented here, using the same beam options, trie and token reduction.
"""

from itertools import groupby
from typing import NamedTuple

import torch


class _Hypothesis(NamedTuple):
    tokens: torch.Tensor
    words: list[str]
    score: float
    timesteps: torch.Tensor


class _Decoder:
    def __init__(self, decoder, lm, tokens_dict, word_dict, blank):
        self.decoder = decoder
        # Native decoders retain references: keep Python-owned objects alive too.
        self.lm = lm
        self.tokens_dict = tokens_dict
        self.word_dict = word_dict
        self.blank = blank
        self.nbest = 1

    def __call__(self, emissions, lengths=None):
        if emissions.dtype != torch.float32:
            raise ValueError("emissions must be float32.")
        if not emissions.is_cpu or not emissions.is_contiguous():
            raise RuntimeError("emissions must be a contiguous CPU tensor.")
        if emissions.ndim != 3:
            raise RuntimeError("emissions must be 3D (batch, frames, tokens).")
        batch, frames, tokens = emissions.shape
        if tokens != self.tokens_dict.index_size():
            raise ValueError(
                "emission token count does not match the tokens dictionary."
            )
        if lengths is None:
            lengths = torch.full((batch,), frames, dtype=torch.int64)
        if (
            not lengths.is_cpu
            or lengths.shape != (batch,)
            or lengths.dtype not in (torch.int32, torch.int64)
            or torch.any(lengths < 0)
            or torch.any(lengths > frames)
        ):
            raise ValueError(
                "lengths must contain one valid CPU integer per batch item."
            )
        hypotheses = []
        for index, length in enumerate(lengths.tolist()):
            pointer = (
                emissions.data_ptr()
                + emissions.element_size() * index * emissions.stride(0)
            )
            results = self.decoder.decode(pointer, length, tokens)
            hypotheses.append(
                [
                    _Hypothesis(
                        torch.tensor(
                            [
                                token
                                for token, _ in groupby(result.tokens)
                                if token != self.blank
                            ],
                            dtype=torch.int64,
                        ),
                        [
                            self.word_dict.get_entry(word)
                            for word in result.words
                            if word >= 0
                        ],
                        result.score,
                        torch.tensor(
                            [
                                i
                                for i, token in enumerate(result.tokens)
                                if token != self.blank
                                and (i == 0 or token != result.tokens[i - 1])
                            ],
                            dtype=torch.int32,
                        ),
                    )
                    for result in results[:1]
                ]
            )
        return hypotheses

    def idxs_to_tokens(self, indices):
        return [self.tokens_dict.get_entry(int(index)) for index in indices]


def ctc_decoder(*, lexicon, tokens, lm, lm_weight, blank_token, sil_token, unk_word):
    """Construct PyLaia's offline decoder with TorchAudio-compatible defaults."""
    from flashlight.lib.text.decoder import (
        CriterionType,
        LexiconDecoder,
        LexiconDecoderOptions,
        LexiconFreeDecoder,
        LexiconFreeDecoderOptions,
        SmearingMode,
        Trie,
        ZeroLM,
    )
    from flashlight.lib.text.decoder.kenlm import KenLM
    from flashlight.lib.text.dictionary import Dictionary, create_word_dict, load_words

    tokens_dict = Dictionary(tokens)
    lexicon = load_words(lexicon) if lexicon else None
    if lexicon:
        word_dict = create_word_dict(lexicon)
    else:
        vocabulary = {
            tokens_dict.get_entry(i): [[tokens_dict.get_entry(i)]]
            for i in range(tokens_dict.index_size())
        }
        vocabulary[unk_word] = [[unk_word]]
        word_dict = create_word_dict(vocabulary)
    lm = KenLM(lm, word_dict) if isinstance(lm, str) else ZeroLM()
    blank = tokens_dict.get_index(blank_token)
    silence = tokens_dict.get_index(sil_token)
    options = dict(
        beam_size=50,
        beam_size_token=tokens_dict.index_size(),
        beam_threshold=50.0,
        lm_weight=lm_weight,
        sil_score=0.0,
        log_add=False,
        criterion_type=CriterionType.CTC,
    )
    if lexicon:
        trie = Trie(tokens_dict.index_size(), silence)
        start = lm.start(False)
        for word, spellings in lexicon.items():
            word_index = word_dict.get_index(word)
            _, score = lm.score(start, word_index)
            for spelling in spellings:
                trie.insert(
                    [tokens_dict.get_index(token) for token in spelling],
                    word_index,
                    score,
                )
        trie.smear(SmearingMode.MAX)
        decoder = LexiconDecoder(
            LexiconDecoderOptions(word_score=0.0, unk_score=float("-inf"), **options),
            trie,
            lm,
            silence,
            blank,
            word_dict.get_index(unk_word),
            [],
            False,
        )
    else:
        decoder = LexiconFreeDecoder(
            LexiconFreeDecoderOptions(**options), lm, silence, blank, []
        )
    return _Decoder(decoder, lm, tokens_dict, word_dict, blank)
