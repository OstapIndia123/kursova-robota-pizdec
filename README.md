# IFNTUNG OOP Coursework 2026 — Variant 6

Console application for calculating the ratio of a 3D shape's volume to its **total external surface area**. Supported shapes are a right circular cone, right circular cylinder, and general tetrahedron. The total-area interpretation is an academic assumption and still requires instructor confirmation.

## Build and test

Requirements: a C++17 compiler and CMake 3.16 or newer.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

## Run

```sh
./build/shape_ratio
```

Enter the input TXT path. At the output prompt, press Enter to use `<input-stem>.out.txt` in the input directory, or enter an output path. The program refuses paths that resolve to the same file. Results and record errors are written with identical formatting to the console and output file. The program continues after bad records and returns a nonzero status if any record was invalid.

## Input format

UTF-8, one whitespace-separated record per line. Blank lines and text after `#` are ignored. Decimal numbers use `.`. Units are consistent user-selected linear units; the ratio has units of length.

```text
cone <radius> <height>
cylinder <radius> <height>
tetrahedron <Ax> <Ay> <Az> <Bx> <By> <Bz> <Cx> <Cy> <Cz> <Dx> <Dy> <Dz>
```

See [`examples/shapes.txt`](examples/shapes.txt). Dimensions must be finite and positive. Tetrahedron vertices must be finite and non-coplanar. Near-coplanarity is rejected when the absolute determinant is at most `1e-12 * L^3`, where `L` is the largest pairwise vertex distance. Intermediate values are not rounded. Output uses the classic C locale, a dot decimal separator, fixed notation, and 10 digits after the decimal point.

For the included sample, the computed values are:

```text
line=2 type=cone volume=37.6991118431 surface_area=75.3982236862 ratio=0.5000000000
line=3 type=cylinder volume=62.8318530718 surface_area=87.9645943005 ratio=0.7142857143
line=4 type=tetrahedron volume=0.1666666667 surface_area=2.3660254038 ratio=0.0704416218
```

## Design

- `Shape3D` is an abstract interface with virtual `volume`, `surfaceArea`, and `typeName` methods; `ratio` is shared.
- `Cone`, `Cylinder`, and `Tetrahedron` provide the shape-specific calculations.
- `Vector3D` holds tetrahedron coordinates and basic vector operations.
- `ShapeFactory` creates polymorphic shapes held by `std::unique_ptr<Shape3D>`.
- `FileProcessor` parses records and returns line-numbered errors while continuing through the file.
- `ResultWriter` creates matching console/file output and protects the input from same-file truncation.

The input format identifies cone and cylinder by radius and height, and tetrahedron by four points. Cone and cylinder are assumed to be right circular shapes. The tetrahedron degeneracy tolerance is a documented numerical policy, not an instructor-approved academic rule.
