# CRT Encoding and Reconstruction

Leaf nodes may compact several numeric values into a single integer using the
Chinese Remainder Theorem (CRT).  The residues and their moduli are transmitted
in the payload under the `crt` key:

```json
"crt": {"m": [65521,65519,65497,65479,65449], "r": [<int>, ...]}
```

At the Raspberry Pi gateway the original value is recovered using **Garner's
algorithm**.  Garner's method incrementally reconstructs the unique integer `x`
that satisfies `x ≡ r_i (mod m_i)` for all residues.  Starting with `x = 0` and
a running product `M = 1`, each pair `(r_i, m_i)` updates the accumulator:

1. Compute the partial inverse `inv = M^{-1} (mod m_i)`.
2. Set `x = x + (r_i - x) * inv * M`.
3. Update `M = M * m_i`.

After processing all residues, `x` holds the packed integer which can then be
unpacked into the original stats or hashes.
