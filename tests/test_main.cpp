#include "cone.hpp"
#include "cylinder.hpp"
#include "file_processor.hpp"
#include "result_writer.hpp"
#include "shape_factory.hpp"
#include "tetrahedron.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
int assertions = 0;

void check(bool condition, const std::string& message) {
    ++assertions;
    if (!condition) throw std::runtime_error(message);
}

void near(double actual, double expected, const std::string& message,
          double tolerance = 1e-10) {
    check(std::isfinite(actual) && std::abs(actual - expected) <=
          std::max(std::numeric_limits<double>::denorm_min() * 16.0,
                   tolerance * std::abs(expected)), message);
}

template <typename Function>
void throws(Function function, const std::string& message) {
    bool didThrow = false;
    try { function(); } catch (const std::exception&) { didThrow = true; }
    check(didThrow, message);
}

class TemporaryDirectory {
public:
    TemporaryDirectory() {
        const auto base = std::filesystem::temp_directory_path() /
            ("oop-coursework-2026-tests-" + std::to_string(
                std::chrono::steady_clock::now().time_since_epoch().count()));
        for (unsigned int attempt = 0; attempt < 100; ++attempt) {
            path_ = base;
            if (attempt != 0) path_ += "-" + std::to_string(attempt);
            std::error_code error;
            if (std::filesystem::create_directory(path_, error)) return;
            if (error) throw std::filesystem::filesystem_error("create test directory", path_, error);
        }
        throw std::runtime_error("could not create a unique test directory");
    }

    ~TemporaryDirectory() {
        std::error_code ignored;
        std::filesystem::remove_all(path_, ignored);
    }

    const std::filesystem::path& path() const noexcept { return path_; }

private:
    std::filesystem::path path_;
};

TemporaryDirectory testDirectory() {
    return TemporaryDirectory{};
}

void geometryTests() {
    const Cone cone(3.0, 4.0);
    const double pi = std::acos(-1.0);
    near(cone.volume(), 12.0 * pi, "cone volume");
    near(cone.surfaceArea(), 24.0 * pi, "cone total surface area");
    near(cone.ratio(), 0.5, "cone ratio");

    const Cylinder cylinder(2.0, 5.0);
    near(cylinder.volume(), 20.0 * pi, "cylinder volume");
    near(cylinder.surfaceArea(), 28.0 * pi, "cylinder total surface area");
    near(cylinder.ratio(), 5.0 / 7.0, "cylinder ratio");

    const Tetrahedron unit({0, 0, 0}, {1, 0, 0}, {0, 1, 0}, {0, 0, 1});
    near(unit.volume(), 1.0 / 6.0, "general tetrahedron volume");
    near(unit.surfaceArea(), (3.0 + std::sqrt(3.0)) / 2.0, "general tetrahedron area");
    near(unit.ratio(), (1.0 / 6.0) / ((3.0 + std::sqrt(3.0)) / 2.0), "general tetrahedron ratio");

    const double root3 = std::sqrt(3.0);
    const double root2over3 = std::sqrt(2.0 / 3.0);
    const Tetrahedron regular({0, 0, 0}, {1, 0, 0}, {0.5, root3 / 2.0, 0},
                              {0.5, root3 / 6.0, root2over3});
    near(regular.volume(), std::sqrt(2.0) / 12.0, "regular tetrahedron reference");
    near(regular.surfaceArea(), root3, "regular tetrahedron surface reference");
    near(regular.ratio(), 1.0 / (6.0 * std::sqrt(6.0)), "regular tetrahedron ratio");

    const Tetrahedron translated({3,-7,11}, {4,-7,11}, {3,-6,11}, {3,-7,12});
    near(translated.volume(), unit.volume(), "tetrahedron translation-invariant volume");
    near(translated.surfaceArea(), unit.surfaceArea(), "tetrahedron translation-invariant area");
    const Tetrahedron permuted({0,0,1}, {0,1,0}, {1,0,0}, {0,0,0});
    near(permuted.volume(), unit.volume(), "tetrahedron vertex-permutation-invariant volume");
    near(permuted.surfaceArea(), unit.surfaceArea(), "tetrahedron vertex-permutation-invariant area");

    for (const double scale : {1e-100, 1e100}) {
        const Cone scaledCone(3.0 * scale, 4.0 * scale);
        near(scaledCone.volume(), 12.0 * pi * scale * scale * scale,
             "cone scale test volume");
        near(scaledCone.surfaceArea(), 24.0 * pi * scale * scale,
             "cone scale test area");
        near(scaledCone.ratio(), 0.5 * scale, "cone scale test ratio");

        const Cylinder scaledCylinder(2.0 * scale, 5.0 * scale);
        near(scaledCylinder.volume(), 20.0 * pi * scale * scale * scale,
             "cylinder scale test volume");
        near(scaledCylinder.surfaceArea(), 28.0 * pi * scale * scale,
             "cylinder scale test area");
        near(scaledCylinder.ratio(), (5.0 / 7.0) * scale,
             "cylinder scale test ratio");

        const Tetrahedron scaledTetra({0,0,0}, {scale,0,0}, {0,scale,0}, {0,0,scale});
        near(scaledTetra.volume(), scale * scale * scale / 6.0,
             "tetrahedron scale test volume");
        near(scaledTetra.surfaceArea(), (3.0 + std::sqrt(3.0)) * scale * scale / 2.0,
             "tetrahedron scale test area");
    }
    const double largeScale = 1e103;
    const Tetrahedron largeThin({0,0,0}, {largeScale,0,0}, {0,largeScale,0},
                                {0,0,largeScale * 1e-11});
    check(std::isfinite(largeThin.volume()) && largeThin.volume() > 0.0,
          "large thin tetrahedron remains valid when scaled determinant is representable");
    const Tetrahedron maximumRepresentableVolume({0,0,0}, {largeScale,0,0},
                                                  {0,largeScale,0}, {0,0,largeScale});
    near(maximumRepresentableVolume.volume(), 1e308 * (10.0 / 6.0),
         "tetrahedron final volume can fit when its raw determinant overflows");
}

void validationTests() {
    throws([] { Cone(0, 1); }, "zero cone radius rejected");
    throws([] { Cone(1, -1); }, "negative cone height rejected");
    throws([] { Cylinder(INFINITY, 1); }, "infinite cylinder parameter rejected");
    throws([] { Cylinder(1e200, 1e200); }, "overflowing cylinder rejected");
    throws([] { Cylinder(1e-200, 1e-200); }, "underflowing cylinder rejected");
    throws([] { Tetrahedron({0,0,0}, {1,0,0}, {0,1,0}, {1,1,0}); }, "coplanar tetrahedron rejected");
    throws([] { Tetrahedron({0,0,0}, {1,0,0}, {0,1,0}, {0,0,1e-13}); },
           "tetrahedron below relative volume tolerance rejected");
    const Tetrahedron aboveTolerance({0,0,0}, {1,0,0}, {0,1,0}, {0,0,1e-10});
    check(aboveTolerance.volume() > 0.0, "tetrahedron above relative volume tolerance accepted");
    throws([] { Tetrahedron({0,0,0}, {0,0,0}, {0,1,0}, {0,0,1}); }, "repeated tetrahedron vertex rejected");
    throws([] { Tetrahedron({0,0,0}, {1,0,0}, {0,1,0}, {0,0,INFINITY}); }, "nonfinite coordinate rejected");
    throws([] { ShapeFactory::create("cone", {1.0}); }, "missing parameters rejected");
    throws([] { ShapeFactory::create("sphere", {1.0, 2.0}); }, "unknown shape rejected");
}

void fileTests(const std::filesystem::path& dir) {
    const auto input = dir / "mixed.txt";
    {
        std::ofstream file(input);
        file << "# mixed sample\n\ncone 3 4\nunknown 1 2\ncylinder 2 5 extra\n"
             << "tetrahedron 0 0 0 1 0 0 0 1 0 0 0 1\ncone nan 2\ncone inf 2\ncone 0x1p2 2\n";
    }
    const auto results = FileProcessor{}.process(input);
    check(results.size() == 7, "blank/comment lines ignored and seven records returned");
    check(results[0].lineNumber == 3 && results[0].error.empty(), "valid cone line number");
    check(results[1].lineNumber == 4 && !results[1].error.empty(), "unknown shape has line error");
    check(results[2].lineNumber == 5 && !results[2].error.empty(), "extra parameter rejected");
    check(results[3].lineNumber == 6 && results[3].error.empty(), "valid tetrahedron after invalid records");
    check(results[4].lineNumber == 7 && !results[4].error.empty(), "nonfinite token rejected");
    check(results[5].lineNumber == 8 && !results[5].error.empty(), "infinity token rejected");
    check(results[6].lineNumber == 9 && !results[6].error.empty(), "non-decimal numeric syntax rejected");

    std::ostringstream console;
    const auto output = dir / "results.txt";
    ResultWriter::write(results, console, output, input);
    std::ifstream outputFile(output);
    std::ostringstream fileContents;
    fileContents << outputFile.rdbuf();
    check(console.str() == fileContents.str(), "console and file output match byte-for-byte");
    check(console.str().find("line=3 type=cone volume=37.6991118431") != std::string::npos,
          "fixed decimal precision and dot decimal separator");

    throws([&] { std::ostringstream out; ResultWriter::write(results, out, input, input); },
           "identical input/output path rejected");
    const auto alias = dir / "mixed-alias.txt";
    std::error_code filesystemError;
    std::filesystem::create_hard_link(input, alias, filesystemError);
    if (!filesystemError) {
        throws([&] { std::ostringstream out; ResultWriter::write(results, out, alias, input); },
               "hard-link input/output alias rejected");
    }
    filesystemError.clear();
    const auto symlink = dir / "mixed-symlink.txt";
    std::filesystem::create_symlink(input, symlink, filesystemError);
    if (!filesystemError) {
        throws([&] { std::ostringstream out; ResultWriter::write(results, out, symlink, input); },
               "symlink input/output alias rejected");
    }
    const auto relativeAliasDir = dir / "subdir";
    std::filesystem::create_directories(relativeAliasDir);
    const auto relativeAlias = dir / "subdir" / ".." / "mixed.txt";
    throws([&] { std::ostringstream out; ResultWriter::write(results, out, relativeAlias, input); },
           "normalized relative input/output alias rejected");
    std::ifstream preserved(input);
    std::string firstLine;
    std::getline(preserved, firstLine);
    check(firstLine == "# mixed sample", "same-file guard preserves input file");

    const auto empty = dir / "empty.txt";
    { std::ofstream file(empty); }
    throws([&] { (void)FileProcessor{}.process(empty); }, "physically empty file rejected");
    { std::ofstream file(empty); file << " # only comment\n\n"; }
    throws([&] { (void)FileProcessor{}.process(empty); }, "empty logical input rejected");
    throws([&] { (void)FileProcessor{}.process(dir / "missing.txt"); }, "missing input rejected");
    const auto malformed = dir / "malformed.txt";
    { std::ofstream file(malformed); file << "cone nope 2\n"; }
    const auto malformedResults = FileProcessor{}.process(malformed);
    check(malformedResults.size() == 1 && !malformedResults[0].error.empty(), "nonnumeric value reported");
    throws([&] {
        std::ostringstream out;
        ResultWriter::write(results, out, dir / "missing-parent" / "output.txt", input);
    }, "unwritable output path reported");
}
}

int main() {
    try {
        geometryTests();
        validationTests();
        const auto directory = testDirectory();
        fileTests(directory.path());
        std::cout << "All " << assertions << " assertions passed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Test failure after " << assertions << " assertions: " << error.what() << '\n';
        return 1;
    }
}
