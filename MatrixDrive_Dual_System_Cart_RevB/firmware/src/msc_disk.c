/* SPDX-License-Identifier: MIT */
#include "msc_disk.h"
#include "board_pins.h"
#include "spi_nor.h"
#include "status.h"
#include "tusb.h"
#include <string.h>

#define SCSI_SYNCHRONIZE_CACHE_10 0x35u

static volatile bool install_requested;
static bool medium_present = true;

bool msc_take_install_request(void) {
    if (!install_requested) return false;
    install_requested = false;
    return true;
}

bool msc_request_manual_install(void) {
    if (!storage_flush()) return false;
    medium_present = false;
    install_requested = true;
    return true;
}

void tud_mount_cb(void) {
    medium_present = true;
    status_set(STATUS_USB_MOUNTED);
}

void tud_umount_cb(void) {
    (void)storage_flush();
}

void tud_suspend_cb(bool remote_wakeup_en) {
    (void)remote_wakeup_en;
    (void)storage_flush();
}

void tud_resume_cb(void) {
    if (medium_present) status_set(STATUS_USB_MOUNTED);
}

void tud_msc_inquiry_cb(uint8_t lun, uint8_t vendor_id[8],
                        uint8_t product_id[16], uint8_t product_rev[4]) {
    (void)lun;
    memcpy(vendor_id, "MATRIX  ", 8);
    memcpy(product_id, "DUAL USB CART   ", 16);
    memcpy(product_rev, "B001", 4);
}

bool tud_msc_test_unit_ready_cb(uint8_t lun) {
    if (medium_present) return true;
    tud_msc_set_sense(lun, SCSI_SENSE_NOT_READY, 0x3au, 0x00u);
    return false;
}

void tud_msc_capacity_cb(uint8_t lun, uint32_t *block_count,
                         uint16_t *block_size) {
    (void)lun;
    *block_count = MSC_BLOCK_COUNT;
    *block_size = MSC_BLOCK_BYTES;
}

bool tud_msc_is_writable_cb(uint8_t lun) {
    (void)lun;
    return medium_present;
}

int32_t tud_msc_read10_cb(uint8_t lun, uint32_t lba, uint32_t offset,
                          void *buffer, uint32_t bufsize) {
    (void)lun;
    const uint32_t address = lba * MSC_BLOCK_BYTES + offset;
    if (!medium_present || address > STAGE_FLASH_BYTES ||
        bufsize > STAGE_FLASH_BYTES - address ||
        !storage_read_bytes(address, buffer, bufsize)) return -1;
    return (int32_t)bufsize;
}

int32_t tud_msc_write10_cb(uint8_t lun, uint32_t lba, uint32_t offset,
                           uint8_t *buffer, uint32_t bufsize) {
    (void)lun;
    const uint32_t address = lba * MSC_BLOCK_BYTES + offset;
    if (!medium_present || address > STAGE_FLASH_BYTES ||
        bufsize > STAGE_FLASH_BYTES - address ||
        !storage_write_bytes(address, buffer, bufsize)) return -1;
    status_set(STATUS_USB_WRITING);
    return (int32_t)bufsize;
}

void tud_msc_write10_complete_cb(uint8_t lun) {
    (void)lun;
    /* The 4 KiB cache is flushed on block change, SYNC CACHE or eject. */
    if (medium_present) status_set(STATUS_USB_MOUNTED);
}

bool tud_msc_start_stop_cb(uint8_t lun, uint8_t power_condition,
                           bool start, bool load_eject) {
    (void)lun;
    (void)power_condition;
    if (!load_eject) return true;
    if (start) {
        medium_present = true;
        status_set(STATUS_USB_MOUNTED);
        return true;
    }
    if (!storage_flush()) {
        status_set(STATUS_FLASH_ERROR);
        return false;
    }
    medium_present = false;
    install_requested = true;
    return true;
}

int32_t tud_msc_scsi_cb(uint8_t lun, const uint8_t scsi_cmd[16],
                        void *buffer, uint16_t bufsize) {
    (void)buffer;
    (void)bufsize;
    if (scsi_cmd[0] == SCSI_SYNCHRONIZE_CACHE_10)
        return storage_flush() ? 0 : -1;
    tud_msc_set_sense(lun, SCSI_SENSE_ILLEGAL_REQUEST, 0x20u, 0x00u);
    return -1;
}
