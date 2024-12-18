"""MCP2221A driver subclass

This is a fix for the EasyMCP2221 library that does not handle
some states correctly.
"""
import time
import EasyMCP2221
from EasyMCP2221.exceptions import NotAckError
from EasyMCP2221.Constants import CMD_I2C_WRITE_DATA, CMD_I2C_WRITE_DATA_REPEATED_START, CMD_I2C_WRITE_DATA_NO_STOP, \
                                RESPONSE_STATUS_BYTE, RESPONSE_RESULT_OK, I2C_INTERNAL_STATUS_BYTE,\
                                I2C_ST_WRITEDATA, I2C_ST_WRITEDATA_WAITSEND, I2C_ST_WRITEDATA_ACK, \
                                I2C_ST_WRITEDATA_TOUT, I2C_ST_STOP_TOUT, I2C_ST_WRITEDATA_END_NOSTOP, \
                                I2C_ST_IDLE, I2C_CHUNK_SIZE, \
                                I2C_ST_WRADDRL, I2C_ST_WRADDRL_WAITSEND, I2C_ST_WRADDRL_ACK, \
                                I2C_ST_WRADDRL_NACK_STOP_PEND, I2C_ST_WRADDRL_NACK_STOP, I2C_ST_WRADDRL_TOUT, \
                                CMD_I2C_READ_DATA, CMD_I2C_READ_DATA_REPEATED_START, CMD_I2C_READ_DATA_GET_I2C_DATA, \
                                I2C_ST_READDATA, I2C_ST_READDATA_ACK, I2C_ST_READDATA_WAIT, I2C_ST_READDATA_WAITGET, \
                                I2C_ST_STOP, I2C_ST_STOP_WAIT \

class MCP2221A(EasyMCP2221.Device):
    """easyMCP2221 device subclass
    """
    def I2C_write(self, addr, data, kind = "regular", timeout_ms = 20):
        """ Write data to an address on I2C bus.

        Valid values for ``kind`` are:

            regular
                It will send **start**, *data*, **stop** (this is the default)
            restart
                It will send **repeated start**, *data*, **stop**
            nonstop
                It will send **start**, data to write, (no stop). Please note that you must use
                'restart' mode to read or write after a *nonstop* write.

        Parameters:
            addr (int): I2C slave device **base** address.
            data (bytes): bytes to write. Maximum length is 65535 bytes, minimum is 1.
            kind (str, optional): kind of transfer (see description).
            timeout_ms (int, optional): maximum time to write data chunk in milliseconds (default 20 ms).
                Note this time applies for each 60 bytes chunk.
                The whole write operation may take much longer.

        Raises:
            ValueError: if any parameter is not valid.
            NotAckError: if the I2C slave didn't acknowledge.
            TimeoutError: if the writing timeout is exceeded.
            LowSDAError: if I2C engine detects the **SCL** line does not go up (read exception description).
            LowSCLError: if I2C engine detects the **SDA** line does not go up (read exception description).
            RuntimeError: if some other error occurs.

        Examples:
            >>> mcp.I2C_write(0x50, b'This is data')
            >>>

            Writing data to a non-existent device:

            >>> mcp.I2C_write(0x60, b'This is data'))
            Traceback (most recent call last):
            ...
            EasyMCP2221.exceptions.NotAckError: Device did not ACK.

        Note:
            MCP2221 writes data in 60-byte chunks.

            The default timeout of 20 ms is twice the time required to send 60 bytes at
            the minimum supported rate (47 kHz).

            MCP2221's internal I2C engine has additional timeout controls.
        """
        if addr < 0 or addr > 127:
            raise ValueError("Slave address not valid.")

        # If data length is 0, MCP2221 will do nothing at all
        if len(data) < 1:
            raise ValueError("Minimum data length is 1 byte.")
        elif len(data) > 2**16-1:
            raise ValueError("Data too long (max. 65535).")

        if kind == "regular":
            cmd = CMD_I2C_WRITE_DATA
        elif kind == "restart":
            cmd = CMD_I2C_WRITE_DATA_REPEATED_START
        elif kind == "nonstop":
            cmd = CMD_I2C_WRITE_DATA_NO_STOP
        else:
            raise ValueError("Invalid kind of transfer. Allowed: 'regular', 'restart', 'nonstop'.")

        # Try to clean last I2C error condition
        # Also test for bus confusion due to external SDA activity
        if self.status["i2c_dirty"] or self._i2c_status()["confused"]:
            self._i2c_release()

        header = [0] * 4
        header[0] = cmd
        header[1] = len(data)      & 0xFF
        header[2] = len(data) >> 8 & 0xFF
        header[3] = addr << 1      & 0xFF

        chunks = [data[i:i+I2C_CHUNK_SIZE] for i in range(0, len(data), I2C_CHUNK_SIZE)]

        # send data in 60 bytes chunks, repeating the header above
        for chunk in chunks:

            watchdog = time.perf_counter() + timeout_ms/1000

            while True:
                # Protect against infinite loop due to noise in I2C bus
                if time.perf_counter() > watchdog:
                    self._i2c_release()
                    raise TimeoutError("Timeout.")


                # Send more data when buffer is empty.
                rbuf = self.send_cmd(header + list(chunk))

                # data sent, ok, try to send next chunk
                if rbuf[RESPONSE_STATUS_BYTE] == RESPONSE_RESULT_OK:
                    break

                # data not sent, why?
                else:
                    # MCP2221 state machine is busy, try again until timeout
                    if rbuf[I2C_INTERNAL_STATUS_BYTE] in (
                        I2C_ST_WRADDRL,
                        I2C_ST_WRADDRL_WAITSEND,
                        I2C_ST_WRADDRL_ACK,
                        I2C_ST_WRADDRL_NACK_STOP_PEND,
                        I2C_ST_WRITEDATA,
                        I2C_ST_WRITEDATA_WAITSEND,
                        I2C_ST_WRITEDATA_ACK):
                        continue

                    # internal timeout condition
                    elif rbuf[I2C_INTERNAL_STATUS_BYTE] in (
                        I2C_ST_WRITEDATA_TOUT,
                        I2C_ST_STOP_TOUT):
                        self._i2c_release()
                        raise RuntimeError("Internal I2C engine timeout.")

                    # device did not ack last transfer
                    elif rbuf[I2C_INTERNAL_STATUS_BYTE] == I2C_ST_WRADDRL_NACK_STOP:
                        self._i2c_release()
                        raise NotAckError("Device did not ACK.")

                    # after non-stop
                    elif rbuf[I2C_INTERNAL_STATUS_BYTE] == I2C_ST_WRITEDATA_END_NOSTOP:
                        self._i2c_release()
                        raise RuntimeError("You must use 'restart' mode to write after a 'nonstop' write.")

                    # something else
                    else:
                        self._i2c_release()
                        raise RuntimeError(f"I2C write error. Internal status {rbuf[I2C_INTERNAL_STATUS_BYTE]:02x}."
                                           " Try again.")

        # check final status using CMD_POLL_STATUS_SET_PARAMETERS instead another write
        watchdog = time.perf_counter() + timeout_ms/1000

        while True:
            # Protect against infinite loop due to noise in I2C bus
            if time.perf_counter() > watchdog:
                self._i2c_release()
                raise TimeoutError("Timeout.")

            i2c_status = self._i2c_status()

            if i2c_status["st"] in (I2C_ST_IDLE, I2C_ST_WRITEDATA_END_NOSTOP):
                return

            # data not sent, why?
            else:
                # MCP2221 state machine is busy, try again until timeout
                if i2c_status["st"] in (
                    I2C_ST_WRADDRL,
                    I2C_ST_WRADDRL_WAITSEND,
                    I2C_ST_WRADDRL_ACK,
                    I2C_ST_WRADDRL_NACK_STOP_PEND,
                    I2C_ST_WRITEDATA,
                    I2C_ST_WRITEDATA_WAITSEND,
                    I2C_ST_WRITEDATA_ACK,
                    I2C_ST_STOP,
                    I2C_ST_STOP_WAIT
                    ):
                    continue

                # internal timeout condition
                elif i2c_status["st"] in (
                    I2C_ST_WRITEDATA_TOUT,
                    I2C_ST_STOP_TOUT):
                    self._i2c_release()
                    raise RuntimeError("Internal I2C engine timeout.")

                # device did not ack last transfer
                elif i2c_status["st"] == I2C_ST_WRADDRL_NACK_STOP:
                    self._i2c_release()
                    raise NotAckError("Device did not ACK.")

                # after non-stop
                elif i2c_status["st"] == I2C_ST_WRITEDATA_END_NOSTOP:
                    self._i2c_release()
                    raise RuntimeError("You must use 'restart' mode to write after a 'nonstop' write.")

                # something else
                else:
                    self._i2c_release()
                    raise RuntimeError(f"I2C write error. Internal status {i2c_status['st']:02x}. Try again.")



    def I2C_read(self, addr, size = 1, kind = "regular", timeout_ms = 20):
        """ Read data from I2C bus.

        Valid values for ``kind`` are:

            regular
                It will send **start**, *data*, **stop** (this is the default)
            restart
                It will send **repeated start**, *data*, **stop**

        Parameters:
            addr (int): I2C slave device **base** address.
            size (int, optional): how many bytes to read. Maximum is 65535 bytes. Minimum is 1 byte.
            kind (str, optional): kind of transfer (see description).
            timeout_ms (int, optional): time to wait for the data in milliseconds (default 20 ms).
                Note this time applies for each 60 bytes chunk.
                The whole read operation may take much longer.

        Return:
            bytes: data read

        Raises:
            ValueError: if any parameter is not valid.
            NotAckError: if the I2C slave didn't acknowledge.
            TimeoutError: if the writing timeout is exceeded.
            LowSDAError: if I2C engine detects the **SCL** line does not go up (read exception description).
            LowSCLError: if I2C engine detects the **SDA** line does not go up (read exception description).
            RuntimeError: if some other error occurs.

        Examples:

            >>> mcp.I2C_read(0x50, 12)
            b'This is data'

            Write then Read without releasing the bus:

            .. code-block:: python

                >>> mcp.I2C_write(0x50, position, 'nonstop')
                >>> mcp.I2C_read(0x50, length, 'restart')
                b'En un lugar de la Mancha...'

        Hint:
            You can use :func:`I2C_read` with size 1 to check if there is any device listening
            with that address.

            There is a device in ``0x50`` (EEPROM):

            >>> mcp.I2C_read(0x50)
            b'1'

            No device in ``0x60``:

            >>> mcp.I2C_read(0x60)
            Traceback (most recent call last):
            ...
            EasyMCP2221.exceptions.NotAckError: Device did not ACK.


        Note:
            MCP2221 reads data in 60-byte chunks.

            The default timeout of 20 ms is twice the time required to receive 60 bytes at
            the minimum supported rate (47 kHz).
            If a timeout or other error occurs in the middle of character reading, the I2C may get locked.
            See :any:`LowSDAError`.
        """
        if addr < 0 or addr > 127:
            raise ValueError("Slave address not valid.")

        if size < 1:
            raise ValueError("Minimum read size is 1 byte.")
        elif size > 2**16-1:
            raise ValueError("Data too long (max. 65535).")

        if kind == "regular":
            cmd = CMD_I2C_READ_DATA
        elif kind == "restart":
            cmd = CMD_I2C_READ_DATA_REPEATED_START
        else:
            raise ValueError("Invalid kind of transfer. Allowed: 'regular' or 'restart'.")

        # Removed in order to support repeated-start operation.
        #if not self.I2C_is_idle():
        #    raise RuntimeError("I2C read error, engine is not in idle state.")

        # Try to clean last I2C error condition
        if self.status["i2c_dirty"] or self._i2c_status()["confused"]:
            self._i2c_release()

        buf = [0] * 4
        buf[0] = cmd
        buf[1] = size      & 0xFF
        buf[2] = size >> 8 & 0xFF
        buf[3] = (addr << 1 & 0xFF) + 1  # address for read operation

        # Send read command to i2c bus.
        # This command return OK always unless bus were busy.
        # Also triggers data reading and place it into a buffer (until 60 bytes).
        rbuf = self.send_cmd(buf)

        if rbuf[RESPONSE_STATUS_BYTE] != RESPONSE_RESULT_OK:

            self._i2c_release()

            if rbuf[I2C_INTERNAL_STATUS_BYTE] == I2C_ST_WRADDRL_NACK_STOP:
                raise NotAckError("Device did not ACK read command.")

            # after non-stop
            elif rbuf[I2C_INTERNAL_STATUS_BYTE] == I2C_ST_WRITEDATA_END_NOSTOP:
                raise RuntimeError("You must use 'restart' mode to read after a 'nonstop' write.")

            else:
                raise RuntimeError(f"I2C command read error. Internal status {rbuf[I2C_INTERNAL_STATUS_BYTE]:02x}."
                                   " Try again.")


        data = []

        watchdog = time.perf_counter() + timeout_ms/1000

        while True:
            # Protect against infinite loop due to noise in I2C bus
            if time.perf_counter() > watchdog:
                self._i2c_release()
                raise TimeoutError("Timeout.")

            # Try to read  MCP's buffer content
            rbuf = self.send_cmd([CMD_I2C_READ_DATA_GET_I2C_DATA])

            if self.debug_messages:
                print(f"Internal status: {rbuf[I2C_INTERNAL_STATUS_BYTE]:02x}")

            # still reading...
            if rbuf[I2C_INTERNAL_STATUS_BYTE] in (
                I2C_ST_WRADDRL,
                I2C_ST_WRADDRL_WAITSEND,
                I2C_ST_WRADDRL_ACK,
                I2C_ST_WRADDRL_NACK_STOP_PEND,
                I2C_ST_READDATA,
                I2C_ST_READDATA_ACK,
                I2C_ST_STOP_WAIT):
                continue

            # buffer ready, more to come
            elif rbuf[I2C_INTERNAL_STATUS_BYTE] == I2C_ST_READDATA_WAIT:
                chunk_size = rbuf[3]
                data += rbuf[4:4+chunk_size]
                # reset watchdog
                watchdog = time.perf_counter() + timeout_ms/1000
                continue

            # buffer ready, no more data expected
            elif rbuf[I2C_INTERNAL_STATUS_BYTE] == I2C_ST_READDATA_WAITGET:
                chunk_size = rbuf[3]
                data += rbuf[4:4+chunk_size]
                return bytes(data)

            elif rbuf[I2C_INTERNAL_STATUS_BYTE] in (I2C_ST_WRADDRL_NACK_STOP, I2C_ST_WRADDRL_TOUT):
                self._i2c_release()
                raise NotAckError("Device did not ACK read command.")

            else:
                self._i2c_release()
                raise RuntimeError(f"I2C read error. Internal status {rbuf[I2C_INTERNAL_STATUS_BYTE]:02x}.")
