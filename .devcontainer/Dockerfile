FROM mcr.microsoft.com/devcontainers/base:noble


RUN apt-get update -y && \
  apt install -y libgl1 curl software-properties-common wget cmake && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Determine architecture and download appropriate Miniconda installer
USER vscode
WORKDIR /home/vscode
RUN ARCH=$(uname -m) && \
  if [ "$ARCH" = "x86_64" ]; then \
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py312_24.7.1-0-Linux-x86_64.sh"; \
  elif [ "$ARCH" = "aarch64" ]; then \
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py312_24.7.1-0-Linux-aarch64.sh"; \
  else \
    echo "Unsupported architecture: $ARCH"; exit 1; \
  fi && \
  wget $MINICONDA_URL && \
  chmod +x $(basename $MINICONDA_URL) && \
  ./$(basename $MINICONDA_URL) -b && \
  rm $(basename $MINICONDA_URL)


# npx puppeteer browsers install firefox

# Initialize conda and install Python dependencies.
#
# OCP version is pinned to 7.7.2.1 because:
#   - ocp 7.9+ removes the _s static method suffix (e.g. TopoDS.Vertex_s ->
#     TopoDS.Vertex), breaking cadquery 2.5.2 and all nebula OCC call sites.
#   - ocp 7.7.2.1 has a BinTools.Read_s BytesIO seek bug (OCP issue #192)
#     that is worked around in OCCUtils.import_bin via a temp-file write.
#
# ezdxf is installed via pip because conda-forge does not have ezdxf >=1.3.0,
# which is required by newer cadquery versions.
RUN CONDA_PATH=/home/vscode/miniconda3/bin/conda && \
  $CONDA_PATH init && \
  $CONDA_PATH install -n base conda-libmamba-solver -y && \
  $CONDA_PATH config --set solver libmamba && \
  $CONDA_PATH install -n base -c conda-forge "cadquery=2.5.2" "ocp=7.7.2.1"

RUN . /home/vscode/miniconda3/etc/profile.d/conda.sh && \
    conda activate base && \
    pip install "ezdxf>=1.3.0" && \
    pip install git+https://github.com/OpenOrion/jupyter-cadquery.git && \
    pip install lxml_html_clean && \
    pip install git+https://github.com/gumyr/cq_warehouse.git
