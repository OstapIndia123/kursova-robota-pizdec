#pragma once

#include <stdexcept>
#include <string>

class Shape3D {
public:
    virtual ~Shape3D() = default;
    virtual double volume() const = 0;
    virtual double surfaceArea() const = 0;
    virtual std::string typeName() const = 0;

    double ratio() const {
        const double area = surfaceArea();
        if (!(area > 0.0)) {
            throw std::domain_error("surface area must be positive");
        }
        return volume() / area;
    }
};
