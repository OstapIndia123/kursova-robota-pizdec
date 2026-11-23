#pragma once

#include "file_processor.hpp"

#include <filesystem>
#include <iosfwd>
#include <vector>

class ResultWriter {
public:
    static void write(const std::vector<RecordResult>& results,
                      std::ostream& console,
                      const std::filesystem::path& outputPath,
                      const std::filesystem::path& inputPath);
};
