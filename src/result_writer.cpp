#include "result_writer.hpp"

#include "shape3d.hpp"

#include <fstream>
#include <iomanip>
#include <locale>
#include <sstream>
#include <stdexcept>

namespace {
std::filesystem::path normalized(const std::filesystem::path& path) {
    std::error_code error;
    auto result = std::filesystem::weakly_canonical(path, error);
    if (error) result = std::filesystem::absolute(path).lexically_normal();
    return result;
}

void ensureDistinctPaths(const std::filesystem::path& input,
                         const std::filesystem::path& output) {
    if (normalized(input) == normalized(output)) {
        throw std::invalid_argument("input and output paths refer to the same file");
    }
    std::error_code error;
    if (std::filesystem::exists(input, error) && !error &&
        std::filesystem::exists(output, error) && !error &&
        std::filesystem::equivalent(input, output, error) && !error) {
        throw std::invalid_argument("input and output paths refer to the same file");
    }
}

void render(const std::vector<RecordResult>& results, std::ostream& output) {
    output.imbue(std::locale::classic());
    output << std::fixed << std::setprecision(10);
    for (const auto& record : results) {
        if (!record.error.empty()) {
            output << "line=" << record.lineNumber << " type=" << record.shape
                   << " error=" << record.error << '\n';
            continue;
        }
        const double volume = record.object->volume();
        const double area = record.object->surfaceArea();
        const double ratio = record.object->ratio();
        output << "line=" << record.lineNumber << " type=" << record.object->typeName()
               << " volume=" << volume << " surface_area=" << area
               << " ratio=" << ratio << '\n';
    }
    if (!output) throw std::runtime_error("failed while writing results");
}
}

void ResultWriter::write(const std::vector<RecordResult>& results,
                         std::ostream& console,
                         const std::filesystem::path& outputPath,
                         const std::filesystem::path& inputPath) {
    ensureDistinctPaths(inputPath, outputPath);
    std::ostringstream buffer;
    render(results, buffer);
    const std::string content = buffer.str();
    console << content;
    if (!console) throw std::runtime_error("failed while writing results to console");
    std::ofstream output(outputPath, std::ios::out | std::ios::trunc);
    if (!output) throw std::runtime_error("cannot open output file '" + outputPath.string() + "'");
    output.imbue(std::locale::classic());
    output << content;
    output.close();
    if (!output) throw std::runtime_error("failed while writing output file '" + outputPath.string() + "'");
}
