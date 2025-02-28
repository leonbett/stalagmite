#!/bin/bash

cp -rT /stalagmite/data_backup/ /stalagmite/data/
python3 /stalagmite/eval/eval.py $@ # Pass all args