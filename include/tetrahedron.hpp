#pragma once

#include "shape3d.hpp"
#include "vector3d.hpp"

class Tetrahedron final : public Shape3D {
public:
    Tetrahedron(Vector3D a, Vector3D b, Vector3D c, Vector3D d);
    double volume() const override;
    double surfaceArea() const override;
    std::string typeName() const override;
private:
    Vector3D a_, b_, c_, d_;
};
