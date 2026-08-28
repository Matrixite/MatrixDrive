YOSYS ?= yosys
IVERILOG ?= iverilog
VVP ?= vvp

RTL = rtl/sms_fm_bus.v rtl/pdm_dac.v rtl/matrixdrive_sms_fm_top.v
CORE = third_party/IKAOPLL/src/IKAOPLL.v \
	third_party/IKAOPLL/src/IKAOPLL_modules/IKAOPLL_dac.v \
	third_party/IKAOPLL/src/IKAOPLL_modules/IKAOPLL_eg.v \
	third_party/IKAOPLL/src/IKAOPLL_modules/IKAOPLL_lfo.v \
	third_party/IKAOPLL/src/IKAOPLL_modules/IKAOPLL_op.v \
	third_party/IKAOPLL/src/IKAOPLL_modules/IKAOPLL_pg.v \
	third_party/IKAOPLL/src/IKAOPLL_modules/IKAOPLL_primitives.v \
	third_party/IKAOPLL/src/IKAOPLL_modules/IKAOPLL_reg.v \
	third_party/IKAOPLL/src/IKAOPLL_modules/IKAOPLL_timinggen.v

.PHONY: all test test-model test-rtl test-core lint synth clean

all: test lint synth

test: test-model test-rtl test-core

test-model:
	python3 tb/test_sms_fm_model.py

test-rtl: build/test_sms_fm_bus build/test_pdm_dac
	$(VVP) build/test_sms_fm_bus
	$(VVP) build/test_pdm_dac

test-core: build/test_ikaopll
	$(VVP) build/test_ikaopll

build/test_sms_fm_bus: rtl/sms_fm_bus.v tb/test_sms_fm_bus.v
	$(IVERILOG) -g2012 -Wall -s test_sms_fm_bus -o $@ $^

build/test_pdm_dac: rtl/pdm_dac.v tb/test_pdm_dac.v
	$(IVERILOG) -g2012 -Wall -s test_pdm_dac -o $@ $^

build/test_ikaopll: tb/test_ikaopll.v $(CORE)
	$(IVERILOG) -g2012 -s test_ikaopll -o $@ $^

lint:
	$(YOSYS) -q -p "read_verilog -sv $(RTL) $(CORE); hierarchy -check -top matrixdrive_sms_fm_top; proc; check"

synth:
	$(YOSYS) -s build/synth_ecp5.ys

clean:
	rm -f build/test_sms_fm_bus build/test_pdm_dac build/test_ikaopll \
		build/test_ikaopll.vcd build/matrixdrive_sms_fm.json
