# Third-party FPGA core

`third_party/IKAOPLL` contains the synthesizable IKAOPLL YM2413 core by
Sehyeon Kim (Raki), pinned from upstream commit
`4d393238d1be33ea428a454956270504f037dfa3`.

Upstream: <https://github.com/ika-musume/IKAOPLL>

IKAOPLL is distributed under the BSD 2-Clause License. The unmodified upstream
license is retained in `third_party/IKAOPLL/LICENSE`. The MatrixDrive wrapper,
bus decode and PDM DAC do not alter core behavior; only trailing whitespace was
normalized in the vendored copy.

The core's accumulated signed output is used. VRC7 alternative patches and
the YM2413 diagnostic data output are not connected.
