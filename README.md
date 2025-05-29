# TurboDesigner
the open-source turbomachinery designer 


![assets/shaft.png](assets/shaft.png)
<p>Axial Shaft</p>

![assets/stage_casing.png](assets/stage_casing.png)
<p>Axial Stage Casing</p>

# About
Turbodesigner is a tool that given [parameters](https://github.com/Turbodesigner/turbodesigner/blob/main/tests/designs/mark1.json) such as pressure ratio and mass flow rate can generate designs using mean-line design, blade flow analysis, and at the end generate a CAD model that can be exported to STL and STEP files.

Currently this generates axial compressors and with further tweaks axial turbopumps for liquid rocket engines

# Assumptions
To avoid feature creep or due to lack of development the following assumption are made:
* `Turbomachinery` is an axial compressor (will suport more in later versions)
* `FlowStation` assumes an Ideal Gas
* Mean line is constant and is based on hub to tip ratio
* Blade calculations are base on the `mean (rm)` station
* Stagger angles are generated with `FreeVortex` (will support more in the future) 
* Blade `airfoil` is only a Double Circular Arc at the moment since other geometries haven't been implemented
* `incidence (i)` and `deviation (delta)` values are defaulted 0 (will get Johnson Method working, but at the moment it is disabled)

There are plans later to make the classes that make calculations
extendable for certain circumstances

# Install
`pip install turbodesigner`


# Setup

## Open in Gitpod
[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/github.com/`/turbodesigner)

or 

```
git clone https://github.com/Turbodesigner/turbodesigner.git
cd turbodesigner
pip install -r requirements.txt
pip install jupyter-cadquery==3.4.0 cadquery-massembly==1.0.0rc0 # for viewing in Jupyter
```

# Help Wanted
Right now there are some items such as verifying calculations, CFD analysis, and adding additional logic for blade analysis. View [Projects](https://github.com/orgs/Turbodesigner/projects/1) tab for specific asks. Please join the [Discord](https://discord.gg/H7qRauGkQ6) for project communications and collaboration. Please consider donating to the [Patreon](https://www.patreon.com/openorion) to support future work on this project.
