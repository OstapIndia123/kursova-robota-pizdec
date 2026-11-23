#include "cylinder.hpp"

#include <cmath>
#include <stdexcept>

namespace {
void validate(double radius, double height) {
    if (!std::isfinite(radius) || !std::isfinite(height) || radius <= 0.0 || height <= 0.0) {
        throw std::invalid_argument("cylinder radius and height must be finite and positive");
    }
}
void ensureFinite(double value) {
    if (!std::isfinite(value)) throw std::overflow_error("cylinder calculation overflowed");
    if (value <= 0.0) throw std::invalid_argument("cylinder calculation is degenerate at this numeric scale");
}
}

Cylinder::Cylinder(double radius, double height) : radius_(radius), height_(height) {
    validate(radius_, height_);
    (void)volume();
    (void)surfaceArea();
}

double Cylinder::volume() const {
    const double result = std::acos(-1.0) * radius_ * radius_ * height_;
    ensureFinite(result);
    return result;
}

double Cylinder::surfaceArea() const {
    const double result = 2.0 * std::acos(-1.0) * radius_ * (radius_ + height_);
    ensureFinite(result);
    return result;
}

std::string Cylinder::typeName() const { return "cylinder"; }
