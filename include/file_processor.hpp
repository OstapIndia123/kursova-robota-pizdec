#pragma once

#include <cstddef>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

#include "shape3d.hpp"

struct RecordResult {
    std::size_t lineNumber{};
    std::string shape;
    std::unique_ptr<Shape3D> object;
    std::string error;
};

class FileProcessor {
public:
    std::vector<RecordResult> process(const std::filesystem::path& inputPath) const;
};
