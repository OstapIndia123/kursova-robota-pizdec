#include "cone.hpp"

#include <cmath>
#include <stdexcept>

namespace {
void validate(double radius, double height) {
    if (!std::isfinite(radius) || !std::isfinite(height) || radius <= 0.0 || height <= 0.0) {
        throw std::invalid_argument("cone radius and height must be finite and positive");
    }
}
void ensureFinite(double value) {
    if (!std::isfinite(value)) throw std::overflow_error("cone calculation overflowed");
    if (value <= 0.0) throw std::invalid_argument("cone calculation is degenerate at this numeric scale");
}
}

Cone::Cone(double radius, double height) : radius_(radius), height_(height) {
    validate(radius_, height_);
    (void)volume();
    (void)surfaceArea();
}

double Cone::volume() const {
    const double result = std::acos(-1.0) * radius_ * radius_ * height_ / 3.0;
    ensureFinite(result);
    return result;
}

double Cone::surfaceArea() const {
    const double slant = std::hypot(radius_, height_);
    const double result = std::acos(-1.0) * radius_ * (radius_ + slant);
    ensureFinite(result);
    return result;
}

std::string Cone::typeName() const { return "cone"; }
