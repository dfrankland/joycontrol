import asyncio
import logging
from asyncio import BaseTransport, BaseProtocol
from typing import Optional, Union, Tuple, Text

from controller import Controller
from report import OutputReport, SubCommand, InputReport

logger = logging.getLogger(__name__)


def controller_protocol_factory(controller: Controller):
    def create_controller_protocol():
        return ControllerProtocol(controller)
    return create_controller_protocol


class ControllerProtocol(BaseProtocol):
    def __init__(self, controller: Controller):
        self.controller = controller

        self.transport = None

        self._data_received = asyncio.Event()

    async def wait_for_output_report(self):
        self._data_received.clear()
        await self._data_received.wait()

    def connection_made(self, transport: BaseTransport) -> None:
        logger.debug('Connection established.')
        self.transport = transport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        raise NotImplementedError()

    def error_received(self, exc: Exception) -> None:
        raise NotImplementedError()

    async def report_received(self, data: Union[bytes, Text], addr: Tuple[str, int]) -> None:
        self._data_received.set()

        try:
            report = OutputReport(list(data))
        except ValueError as v_err:
            logger.warning(f'Report parsing error "{v_err}" - IGNORE')
            return

        # classify sub command
        sub_command = report.get_sub_command()
        logging.info(f'received output report - {sub_command}')
        if sub_command == SubCommand.REQUEST_DEVICE_INFO:
            await self._command_request_device_info(report)

        elif sub_command == SubCommand.SET_SHIPMENT_STATE:
            await self._command_set_shipment_state(report)

        elif sub_command == SubCommand.SPI_FLASH_READ:
            await self._command_spi_flash_read(report)

        elif sub_command == SubCommand.SET_INPUT_REPORT_MODE:
            await self._command_set_input_report_mode(report)

        elif sub_command == SubCommand.TRIGGER_BUTTONS_ELAPSED_TIME:
            await self._command_trigger_buttons_elapsed_time(report)

        elif sub_command == SubCommand.NOT_IMPLEMENTED:
            logger.error(f'Sub command not implemented - ignoring')

    async def _command_request_device_info(self, output_report):
        address = self.transport.get_extra_info('sockname')
        assert address is not None
        bd_address = list(map(lambda x: int(x, 16), address[0].split(':')))

        input_report = InputReport()
        input_report.set_input_report_id(0x21)
        input_report.set_misc()
        input_report.set_ack(0x82)
        #input_report.set_button_status()
        #input_report.set_left_analog_stick()
        #input_report.set_right_analog_stick()
        #input_report.set_vibrator_input()
        input_report.sub_0x02_device_info(bd_address)

        asyncio.ensure_future(self.transport.write(input_report))

    async def _command_set_shipment_state(self, output_report):
        input_report = InputReport()
        input_report.set_input_report_id(0x21)
        input_report.set_misc()
        input_report.set_ack(0x80)
        input_report.sub_0x08_shipment()

        asyncio.ensure_future(self.transport.write(input_report))

    async def _command_spi_flash_read(self, output_report):
        input_report = InputReport()
        input_report.set_input_report_id(0x21)
        input_report.set_misc()
        input_report.set_ack(0x90)
        input_report.sub_0x10_spi_flash_read(output_report)

        asyncio.ensure_future(self.transport.write(input_report))

    async def _command_set_input_report_mode(self, output_report):
        input_report = InputReport()
        input_report.set_input_report_id(0x21)
        input_report.set_misc()
        input_report.set_ack(0x80)
        input_report.sub_0x03_set_input_report_mode()

        asyncio.ensure_future(self.transport.write(input_report))

    async def _command_trigger_buttons_elapsed_time(self, output_report):
        input_report = InputReport()
        input_report.set_input_report_id(0x21)
        input_report.set_misc()
        input_report.set_ack(0x83)
        input_report.sub_0x04_trigger_buttons_elapsed_time()

        asyncio.ensure_future(self.transport.write(input_report))
