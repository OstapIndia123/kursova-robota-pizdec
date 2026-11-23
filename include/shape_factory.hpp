#pragma once

#include "shape3d.hpp"

#include <memory>
#include <string>
#include <vector>

class ShapeFactory {
public:
    static std::unique_ptr<Shape3D> create(const std::string& type,
                                           const std::vector<double>& parameters);
};
