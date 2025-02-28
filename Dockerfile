FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive

# Install prerequisites
RUN apt update && \
		apt install -y \
			file \
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
			llvm-11-tools \
			time && \
		pip3 install \
			wllvm \
			z3-solver \
			fuzzingbook \
			lit \
			markdown \
			graphviz \
			tabulate && \
		update-alternatives --install /usr/bin/python python /usr/bin/python3 1

RUN mkdir /stalagmite
ADD data /stalagmite/data
ADD data /stalagmite/data_backup
ADD eval /stalagmite/eval
ADD subjects /stalagmite/subjects
ADD system_level_grammar /stalagmite/system_level_grammar
ADD config.py /stalagmite/config.py
ADD common.py /stalagmite/common.py
ADD docker_entrypoint.sh /stalagmite/docker_entrypoint.sh
RUN chmod +x /stalagmite/docker_entrypoint.sh
ADD klee.patch /stalagmite/klee.patch
ADD klee-examples.commit /stalagmite/klee-examples.commit

RUN chmod -R a+w /stalagmite

# Set root directory
RUN sed -i 's+root =.*+root = "/stalagmite"+g' /stalagmite/config.py

ENV CPATH="/stalagmite/klee/include"
ENV PATH="/stalagmite/:/stalagmite/system_level_grammar/:/stalagmite/klee/build/bin/:/usr/lib/llvm-11/bin/:${PATH}"
ENV PYTHONPATH="/stalagmite:/stalagmite/system_level_grammar:${PYTHONPATH}"

# Set up klee
RUN cd /stalagmite && \
    git clone https://github.com/klee/klee.git && \
    cd klee && \
    git checkout fc778afc9029c48b78aa59c20cdf3e8223a88081 && \
    git checkout -b stalagmite && \
    git apply /stalagmite/klee.patch

# Build klee-uclibc
RUN cd /stalagmite && \
    git clone https://github.com/klee/klee-uclibc.git && \
	cd klee-uclibc && \
	./configure --make-llvm-lib && \
	make -j$(nproc)

# Build klee-libcxx
RUN cd /stalagmite/klee && \
	LLVM_VERSION=11 SANITIZER_BUILD= BASE=/stalagmite/klee-libcxx REQUIRES_RTTI=1 DISABLE_ASSERTIONS=1 ENABLE_DEBUG=0 ENABLE_OPTIMIZED=1 ./scripts/build/build.sh libcxx

# Build klee
RUN cd /stalagmite/klee && \
	mkdir build && \
	cd build && \
	cmake \
	  -DENABLE_SOLVER_STP=OFF \
	  -DENABLE_SOLVER_Z3=ON \
	  -DENABLE_POSIX_RUNTIME=ON \
	  -DENABLE_KLEE_UCLIBC=ON \
	  -DKLEE_UCLIBC_PATH=/stalagmite/klee-uclibc \
	  -DENABLE_UNIT_TESTS=OFF \
	  -DLLVM_CONFIG_BINARY=/usr/lib/llvm-11/bin/llvm-config \
	  -DLLVMCC=/usr/lib/llvm-11/bin/clang-11 \
	  -DLLVMCXX=/usr/lib/llvm-11/bin/clang++ \
	  -DENABLE_KLEE_LIBCXX=ON \
	  -DKLEE_LIBCXX_DIR=/stalagmite/klee-libcxx/libc++-install-110/ \
	  -DKLEE_LIBCXX_INCLUDE_DIR=/stalagmite/klee-libcxx/libc++-install-110/include/c++/v1/ \
	  .. && \
	make -j${nproc}

ENTRYPOINT ["/stalagmite/docker_entrypoint.sh"]