FROM mcr.microsoft.com/devcontainers/miniconda:0-3

RUN apt-get update -y && \
  apt install -y libgl1-mesa-glx curl && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*



USER vscode
RUN conda init
RUN conda install -n base ipykernel --update-deps --force-reinstall -y
RUN conda install -c conda-forge -c cadquery cadquery=master -y
RUN pip install ezdxf --upgrade
  

# [Optional] If your pip requirements rarely change, uncomment this section to add them to the image.
COPY requirements.txt /home/vscode/tmp/pip-tmp/
RUN pip install -r ~/tmp/pip-tmp/requirements.txt
RUN pip install git+https://github.com/OpenOrion/jupyter-cadquery