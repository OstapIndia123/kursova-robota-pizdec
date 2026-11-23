#include "file_processor.hpp"

#include "shape_factory.hpp"

#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace {
bool isDecimalToken(const std::string& token) {
    std::size_t position = 0;
    if (position < token.size() && (token[position] == '+' || token[position] == '-')) ++position;
    std::size_t digits = 0;
    while (position < token.size() && token[position] >= '0' && token[position] <= '9') {
        ++position;
        ++digits;
    }
    if (position < token.size() && token[position] == '.') {
        ++position;
        while (position < token.size() && token[position] >= '0' && token[position] <= '9') {
            ++position;
            ++digits;
        }
    }
    if (digits == 0) return false;
    if (position < token.size() && (token[position] == 'e' || token[position] == 'E')) {
        ++position;
        if (position < token.size() && (token[position] == '+' || token[position] == '-')) ++position;
        const std::size_t exponentStart = position;
        while (position < token.size() && token[position] >= '0' && token[position] <= '9') ++position;
        if (position == exponentStart) return false;
    }
    return position == token.size();
}

double parseNumber(const std::string& token) {
    if (!isDecimalToken(token)) {
        throw std::invalid_argument("invalid decimal number '" + token + "'");
    }
    errno = 0;
    char* end = nullptr;
    const double value = std::strtod(token.c_str(), &end);
    if (token.empty() || end == token.c_str() || *end != '\0' || errno == ERANGE || !std::isfinite(value)) {
        throw std::invalid_argument("invalid finite number '" + token + "'");
    }
    return value;
}
}

std::vector<RecordResult> FileProcessor::process(const std::filesystem::path& inputPath) const {
    std::ifstream input(inputPath);
    if (!input) throw std::runtime_error("cannot open input file '" + inputPath.string() + "'");

    std::vector<RecordResult> results;
    std::string line;
    std::size_t lineNumber = 0;
    while (std::getline(input, line)) {
        ++lineNumber;
        const auto comment = line.find('#');
        if (comment != std::string::npos) line.erase(comment);
        std::istringstream parser(line);
        std::string type;
        if (!(parser >> type)) continue;

        RecordResult result;
        result.lineNumber = lineNumber;
        result.shape = type;
        try {
            std::vector<double> parameters;
            std::string token;
            while (parser >> token) parameters.push_back(parseNumber(token));
            if (!parser.eof()) throw std::invalid_argument("malformed parameter list");
            result.object = ShapeFactory::create(type, parameters);
            (void)result.object->ratio();
        } catch (const std::exception& error) {
            result.error = error.what();
        }
        results.push_back(std::move(result));
    }
    if (input.bad()) throw std::runtime_error("error while reading input file '" + inputPath.string() + "'");
    if (results.empty()) throw std::runtime_error("input file contains no shape records");
    return results;
}
