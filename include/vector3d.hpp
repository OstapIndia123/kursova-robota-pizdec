#pragma once

#include <cmath>
#include <stdexcept>

struct Vector3D {
    double x{};
    double y{};
    double z{};

    Vector3D operator-(const Vector3D& other) const noexcept {
        return {x - other.x, y - other.y, z - other.z};
    }

    Vector3D operator/(double divisor) const noexcept {
        return {x / divisor, y / divisor, z / divisor};
    }

    Vector3D cross(const Vector3D& other) const noexcept {
        return {y * other.z - z * other.y,
                z * other.x - x * other.z,
                x * other.y - y * other.x};
    }

    double dot(const Vector3D& other) const noexcept {
        return x * other.x + y * other.y + z * other.z;
    }

    double norm() const noexcept { return std::hypot(x, y, z); }

    bool isFinite() const noexcept {
        return std::isfinite(x) && std::isfinite(y) && std::isfinite(z);
    }
};
