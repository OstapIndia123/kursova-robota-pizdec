#include "tetrahedron.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

namespace {
void ensureFinite(double value) {
    if (!std::isfinite(value)) throw std::overflow_error("tetrahedron calculation overflowed");
}
double triangleArea(const Vector3D& p, const Vector3D& q, const Vector3D& r) {
    const double area = 0.5 * (q - p).cross(r - p).norm();
    ensureFinite(area);
    return area;
}

double maximumEdgeLength(const Vector3D& a, const Vector3D& b,
                         const Vector3D& c, const Vector3D& d) {
    const std::array<Vector3D, 4> points{a, b, c, d};
    double scale = 0.0;
    for (std::size_t i = 0; i < points.size(); ++i) {
        for (std::size_t j = i + 1; j < points.size(); ++j) {
            scale = std::max(scale, (points[j] - points[i]).norm());
        }
    }
    return scale;
}

double normalizedDeterminant(const Vector3D& a, const Vector3D& b,
                             const Vector3D& c, const Vector3D& d,
                             double scale) {
    const Vector3D ab = (b - a) / scale;
    const Vector3D ac = (c - a) / scale;
    const Vector3D ad = (d - a) / scale;
    return ab.dot(ac.cross(ad));
}

double scaledCubeProduct(double coefficient, double scale) {
    int scaleExponent = 0;
    int coefficientExponent = 0;
    const double scaleMantissa = std::frexp(scale, &scaleExponent);
    const double coefficientMantissa = std::frexp(coefficient, &coefficientExponent);
    const double mantissaProduct = coefficientMantissa * scaleMantissa * scaleMantissa * scaleMantissa;
    int productExponent = 0;
    const double normalizedMantissa = std::frexp(mantissaProduct, &productExponent);
    const int resultExponent = coefficientExponent + 3 * scaleExponent + productExponent;
    return std::scalbn(normalizedMantissa, resultExponent);
}
}

Tetrahedron::Tetrahedron(Vector3D a, Vector3D b, Vector3D c, Vector3D d)
    : a_(a), b_(b), c_(c), d_(d) {
    if (!a_.isFinite() || !b_.isFinite() || !c_.isFinite() || !d_.isFinite()) {
        throw std::invalid_argument("tetrahedron coordinates must be finite");
    }
    const double scale = maximumEdgeLength(a_, b_, c_, d_);
    if (!std::isfinite(scale) || scale <= 0.0) {
        throw std::invalid_argument("tetrahedron has repeated or invalid vertices");
    }
    const double normalizedDet = normalizedDeterminant(a_, b_, c_, d_, scale);
    ensureFinite(normalizedDet);
    // Compare |det| / L^3 directly to avoid overflow/underflow while forming L^3.
    if (std::abs(normalizedDet) <= 1e-12) {
        throw std::invalid_argument("tetrahedron is degenerate or nearly coplanar");
    }
    (void)surfaceArea();
    (void)volume();
}

double Tetrahedron::volume() const {
    const double scale = maximumEdgeLength(a_, b_, c_, d_);
    const double determinant = normalizedDeterminant(a_, b_, c_, d_, scale);
    const double result = scaledCubeProduct(std::abs(determinant) / 6.0, scale);
    ensureFinite(result);
    if (result <= 0.0) throw std::invalid_argument("tetrahedron volume must be positive");
    return result;
}

double Tetrahedron::surfaceArea() const {
    const double result = triangleArea(a_, b_, c_) + triangleArea(a_, b_, d_) +
                          triangleArea(a_, c_, d_) + triangleArea(b_, c_, d_);
    ensureFinite(result);
    if (result <= 0.0) throw std::invalid_argument("tetrahedron surface area must be positive");
    return result;
}

std::string Tetrahedron::typeName() const { return "tetrahedron"; }
