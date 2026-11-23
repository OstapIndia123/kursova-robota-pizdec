#include "file_processor.hpp"
#include "result_writer.hpp"

#include <filesystem>
#include <iostream>
#include <string>

int main() {
    std::string inputText;
    std::cout << "Input TXT path: ";
    if (!std::getline(std::cin, inputText) || inputText.empty()) {
        std::cerr << "Error: input path is required\n";
        return 2;
    }
    const std::filesystem::path inputPath(inputText);

    std::cout << "Output TXT path (press Enter for <input-stem>.out.txt): ";
    std::string outputText;
    if (!std::getline(std::cin, outputText)) {
        std::cerr << "Error: could not read output path\n";
        return 2;
    }
    std::filesystem::path outputPath;
    if (outputText.empty()) {
        outputPath = inputPath.parent_path() / (inputPath.stem().string() + ".out.txt");
    } else {
        outputPath = outputText;
    }

    try {
        const auto results = FileProcessor{}.process(inputPath);
        ResultWriter::write(results, std::cout, outputPath, inputPath);
        for (const auto& record : results) {
            if (!record.error.empty()) return 1;
        }
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 2;
    }
    return 0;
}
