#pragma once

#include "shape3d.hpp"

class Cylinder final : public Shape3D {
public:
    Cylinder(double radius, double height);
    double volume() const override;
    double surfaceArea() const override;
    std::string typeName() const override;
private:
    double radius_;
    double height_;
};
