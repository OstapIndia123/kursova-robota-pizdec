#include "shape_factory.hpp"

#include "cone.hpp"
#include "cylinder.hpp"
#include "tetrahedron.hpp"

#include <stdexcept>

std::unique_ptr<Shape3D> ShapeFactory::create(const std::string& type,
                                               const std::vector<double>& p) {
    if (type == "cone") {
        if (p.size() != 2) throw std::invalid_argument("cone expects exactly 2 parameters");
        return std::make_unique<Cone>(p[0], p[1]);
    }
    if (type == "cylinder") {
        if (p.size() != 2) throw std::invalid_argument("cylinder expects exactly 2 parameters");
        return std::make_unique<Cylinder>(p[0], p[1]);
    }
    if (type == "tetrahedron") {
        if (p.size() != 12) throw std::invalid_argument("tetrahedron expects exactly 12 parameters");
        return std::make_unique<Tetrahedron>(Vector3D{p[0], p[1], p[2]},
                                              Vector3D{p[3], p[4], p[5]},
                                              Vector3D{p[6], p[7], p[8]},
                                              Vector3D{p[9], p[10], p[11]});
    }
    throw std::invalid_argument("unknown shape identifier '" + type + "'");
}
