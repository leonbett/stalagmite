FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive

# Install prerequisites
RUN apt update && \
		apt install -y \
			build-essential \
			curl \
			libcap-dev \
			git \
			cmake \
			libncurses5-dev \
			unzip \
			libtcmalloc-minimal4 \
			libgoogle-perftools-dev \
			libsqlite3-dev \
			doxygen \
			python3 \
			python3-pip \
			gcc-multilib \
			g++-multilib \
			vim \
            libgraphviz-dev \
			z3 \
			libgc-dev \
            tmux \
            htop \
			clang-11 \
			llvm-11 \
			llvm-11-dev \
			llvm-11-tools && \
		pip3 install \
			wllvm \
			z3-solver \
			fuzzingbook \
			lit \
			markdown \
			graphviz \
			tabulate && \
		update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Set up /staminag
RUN mkdir /staminag
ADD data /staminag/data
# data_backup will be copied to data at the start during runtime, to expose this to the host
# Reason: using -v will copy over host contents to container, deleting contents of data/
ADD data /staminag/data_backup
ADD eval /staminag/eval
ADD generalize /staminag/generalize
ADD subjects /staminag/subjects
ADD config.py /staminag/config.py
ADD common.py /staminag/common.py
ADD klee.patch /staminag/klee.patch

# Set root directory
RUN sed -i 's+root =.*+root = "/staminag"+g' /staminag/config.py

ENV CPATH="/staminag/klee/include:$(CPATH)"
ENV PATH="/staminag/:/staminag/generalize/:/staminag/klee/build/bin/:/usr/lib/llvm-11/bin/:${PATH}"
ENV PYTHONPATH="/staminag:/staminag/generalize:${PYTHONPATH}"

# Set up klee
RUN cd /staminag && \
    git clone https://github.com/klee/klee.git && \
    cd klee && \
    git checkout fc778afc9029c48b78aa59c20cdf3e8223a88081 && \
    git checkout -b staminag && \
    git apply /staminag/klee.patch

# Build klee-uclibc
RUN cd /staminag && \
    git clone https://github.com/klee/klee-uclibc.git && \
	cd klee-uclibc && \
	./configure --make-llvm-lib && \
	make -j$(nproc)

# Build klee
RUN cd /staminag/klee && \
	mkdir build && \
	cd build && \
	cmake \
	  -DENABLE_SOLVER_STP=OFF \
	  -DENABLE_SOLVER_Z3=ON \
	  -DENABLE_POSIX_RUNTIME=ON \
	  -DENABLE_KLEE_UCLIBC=ON \
	  -DKLEE_UCLIBC_PATH=/staminag/klee-uclibc \
	  -DENABLE_UNIT_TESTS=OFF \
	  -DLLVM_CONFIG_BINARY=/usr/lib/llvm-11/bin/llvm-config \
	  -DLLVMCC=/usr/lib/llvm-11/bin/clang-11 \
	  -DLLVMCXX=/usr/lib/llvm-11/bin/clang++ \
	  .. && \
	make -j${nproc}

# Run grammar mining
CMD cp -rT /staminag/data_backup/ /staminag/data/ && \
	cd /staminag/eval && \
    ./tmux_mine_all.sh


# => Data is available at /data/paper/accuracy/csv
# => Run /staminag/eval/gen_tex_tables.py to generated accumulated data as .tex tables
