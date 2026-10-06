import unittest
from itertools import product

import torch

from laia.decoders import CTCNBestDecoder


class CTCNBestDecoderTest(unittest.TestCase):
    def test(self):
        x = torch.tensor(
            [
                [[1.0, 3.0, -1.0, 0.0]],
                [[-1.0, 2.0, -2.0, 3.0]],
                [[1.0, 5.0, 9.0, 2.0]],
                [[-1.0, -2.0, -3.0, -4.0]],
            ]
        )
        decoder = CTCNBestDecoder(4)
        r = decoder(x)
        # Several paths tie. Verify N-best scores against exhaustive enumeration
        # without depending on torch.topk's unspecified tie order.
        scores = sorted(
            (
                sum(x[i, 0, v] for i, v in enumerate(p)).item()
                for p in product(range(4), repeat=4)
            ),
            reverse=True,
        )[:4]
        self.assertEqual(scores, [score for score, _ in r[0]])
        self.assertEqual(4, len({tuple(path) for _, path in r[0]}))
        for score, path in r[0]:
            self.assertEqual(score, sum(x[i, 0, v] for i, v in enumerate(path)).item())
        self.assertEqual(r, decoder(x))


if __name__ == "__main__":
    unittest.main()
