#pragma once

#include "shape3d.hpp"

class Cone final : public Shape3D {
public:
    Cone(double radius, double height);
    double volume() const override;
    double surfaceArea() const override;
    std::string typeName() const override;
private:
    double radius_;
    double height_;
};
