# License

pyitm-ng is a Python port of the NTIA Irregular Terrain Model C++ reference
(https://github.com/NTIA/itm). It is covered by two notices:

- The port's own code (the Python implementation, tests, tooling and documentation
  written for this project) is under the MIT License below.
- The model itself, its algorithms, constants and the reference data files in
  `tests/data/ntia/`, derive from NTIA's software and remain under NTIA's notice
  below (SPDX: `NTIA-PD`).

SPDX-License-Identifier: MIT AND NTIA-PD

## Modifications to the NTIA software

As NTIA's notice requests: this is a modified, derivative work of NTIA/itm (C++,
master `183ad95bd813a8be11009df396e1c631356864b2`, 2024-09-24). Changes, from
2026-04 onward:

- translated from C++ to Python (pyitm-ng 0.1.0, 2026-04-15) with a Pythonic API
  (keyword arguments, enums, dataclass results, exceptions for input errors);
- two input checks the C++ lacks, at entry points where it has undefined behaviour
  (a terrain profile with fewer than 2 points; a PFL whose header declares more
  points than it holds);
- otherwise the arithmetic is unchanged: results are bit-identical to the C++ on
  Linux x86_64 and aarch64 (see README, "Numerical fidelity").

The change history is in CHANGELOG.md.

## MIT License (the port)

Copyright (c) 2026 tedaks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## NTIA notice (the model and reference data), verbatim

SOFTWARE DISCLAIMER / RELEASE

This software was developed by employees of the National Telecommunications and Information Administration (NTIA), an agency of the Federal Government and is provided to you as a public service.  Pursuant to Title 15 United States Code Section 105, works of NTIA employees are not subject to copyright protection within the United States.

The software is provided by NTIA “AS IS.”  NTIA MAKES NO WARRANTY OF ANY KIND, EXPRESS, IMPLIED OR STATUTORY, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT AND DATA ACCURACY. NTIA does not warrant or make any representations regarding the use of the software or the results thereof, including but not limited to the correctness, accuracy, reliability or usefulness of the software. 

To the extent that NTIA holds rights in countries other than the United States, you are hereby granted the non-exclusive irrevocable and unconditional right to print, publish, prepare derivative works and distribute the NTIA software, in any medium, or authorize others to do so on your behalf, on a royalty-free basis throughout the World.

You may improve, modify, and create derivative works of the software or any portion of the software, and you may copy and distribute such modifications or works. Modified works should carry a notice stating that you changed the software and should note the date and nature of any such change.

You are solely responsible for determining the appropriateness of using and distributing the software and you assume all risks associated with its use, including but not limited to the risks and costs of program errors, compliance with applicable laws, damage to or loss of data, programs or equipment, and the unavailability or interruption of operation. This software is not intended to be used in any situation where a failure could cause risk of injury or damage to property. 

Please provide appropriate acknowledgments of NTIA’s creation of the software in any copies or derivative works of this software.
