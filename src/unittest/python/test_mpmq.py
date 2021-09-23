
# Copyright (c) 2021 Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#      http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from mock import patch
from mock import call
from mock import Mock
from mock import MagicMock

from queue import Empty

from mpmq.mpmq import MPmq
from mpmq.mpmq import NoActiveProcesses
from mpmq.handler import queue_handler
from mpmq.mpmq import SLEEP_BEFORE_UPDATING_RESULT

import sys
import datetime
import logging
logger = logging.getLogger(__name__)


class TestMPmq(unittest.TestCase):

    def setUp(self):
        """
        """
        pass

    def tearDown(self):
        """
        """
        pass

    def test__init_Should_SetDefaults_When_Called(self, *patches):
        client = MPmq(function=Mock(__name__='mockfunc'))
        self.assertEqual(client.process_data, [{}])
        self.assertEqual(client.shared_data, {})
        self.assertEqual(client.processes_to_start, 1)

    @patch('mpmq.mpmq.QueueHandlerDecorator')
    def test__init_Should_SetDefaults_When_FunctionNotWrapped(self, queue_handler_patch, *patches):
        function_mock = Mock(__name__='mockfunc')
        client = MPmq(function=function_mock)
        self.assertEqual(client.process_data, [{}])
        self.assertEqual(client.shared_data, {})
        self.assertEqual(client.processes_to_start, 1)
        self.assertEqual(client.function, queue_handler_patch.return_value)

    def test__populate_process_queue_Should_AddToProcessQueue_When_Called(self, *patches):
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)
        client.populate_process_queue()
        self.assertEqual(client.process_queue.qsize(), 3)

    @patch('mpmq.MPmq.start_next_process')
    def test__start_processes_Should_CallStartNextProcess_When_Called(self, start_next_process_patch, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data, processes_to_start=2)
        client.start_processes()
        self.assertEqual(len(start_next_process_patch.mock_calls), 2)

    @patch('mpmq.MPmq.populate_process_queue')
    @patch('mpmq.MPmq.start_next_process')
    def test__start_processes_Should_CallStartNextProcess_When_ProcessesToStartGreaterThanProcessQueueSize(self, start_next_process_patch, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.start_processes()
        self.assertEqual(len(start_next_process_patch.mock_calls), 0)

    @patch('mpmq.mpmq.QueueHandlerDecorator')
    @patch('mpmq.mpmq.Process')
    def test__start_next_process_Should_CallExpected_When_Called(self, process_patch, queue_handler_mock, *patches):
        process_mock = Mock()
        process_patch.return_value = process_mock

        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data, shared_data='--shared-data--')
        client.populate_process_queue()
        client.start_next_process()

        process_patch.assert_called_once_with(
            target=queue_handler_mock.return_value,
            args=({'range': '0-1'}, '--shared-data--'),
            kwargs={
                'message_queue': client.message_queue,
                'offset': 0,
                'result_queue': client.result_queue
            })

    def test__terminate_processes_Should_CallExpected_When_Called(self, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data, shared_data='--shared-data--')
        process1_mock = Mock()
        process2_mock = Mock()
        client.active_processes = {'0': {'process': process1_mock}, '1': {'process': process2_mock}}
        client.terminate_processes()
        process1_mock.terminate.assert_called_once_with()
        process2_mock.terminate.assert_called_once_with()

    def test__purge_process_queue_Should_PurgeProcessQueue_When_Called(self, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.populate_process_queue()
        self.assertEqual(client.process_queue.qsize(), 3)
        client.purge_process_queue()
        self.assertTrue(client.process_queue.empty())

    @patch('mpmq.MPmq.get_end_time_duration', return_value=('--end-time--', '--duration--'))
    @patch('mpmq.mpmq.logger')
    def test__remove_active_process_Should_CallExpected_When_Called(self, logger_patch, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data)
        process_mock = Mock(pid=121372, name='Process-1')
        process_mock.name = 'Process-1'
        client.active_processes['0'] = {'process': process_mock, 'start_time': '--time--'}
        client.remove_active_process('0')
        logger_patch.info.assert_called_once_with('process at offset 0 process id 121372 (Process-1) has completed')
        self.assertEqual(client.durations['0'], '--duration--')
        self.assertEqual(client.finished_processes['0'], {'process': process_mock, 'start_time': '--time--', 'end_time': '--end-time--', 'duration': '--duration--'})

    @patch('mpmq.mpmq.sleep')
    def test__update_result_Should_CallExpected_When_Called(self, sleep_patch, *patches):
        result_queue_mock = Mock()
        result_queue_mock.get.side_effect = [
            {'0': '--result0--'},
            {'1': '--result1--'},
            {'2': '--result2--'},
            Empty('empty')
        ]
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.result_queue = result_queue_mock
        client.update_result()
        expected_process_data = [{'range': '0-1', 'result': '--result0--'}, {'range': '2-3', 'result': '--result1--'}, {'range': '4-5', 'result': '--result2--'}]
        self.assertEqual(client.process_data, expected_process_data)
        sleep_patch.assert_called_once_with(SLEEP_BEFORE_UPDATING_RESULT)

    @patch('mpmq.mpmq.sleep')
    def test__update_result_Should_CallSleep_When_SleepOverride(self, sleep_patch, *patches):
        result_queue_mock = Mock()
        result_queue_mock.get.side_effect = [
            {'0': '--result0--'},
            {'1': '--result1--'},
            {'2': '--result2--'},
            Empty('empty')
        ]
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.result_queue = result_queue_mock
        client.update_result(sleep_time=5)
        expected_process_data = [{'range': '0-1', 'result': '--result0--'}, {'range': '2-3', 'result': '--result1--'}, {'range': '4-5', 'result': '--result2--'}]
        self.assertEqual(client.process_data, expected_process_data)
        sleep_patch.assert_called_once_with(5)

    def test__active_processes_empty_Should_ReturnExpected_When_Called(self, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.active_processes = {'1': True}
        self.assertFalse(client.active_processes_empty())
        client.active_processes = {}
        self.assertTrue(client.active_processes_empty())

    def test__get_message_Should_ReturnExpected_When_ControlDone(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        message_queue_mock = Mock()
        message_queue_mock.get.return_value = '#0-DONE'
        client.message_queue = message_queue_mock

        result = client.get_message()
        expected_result = {
            'offset': '0',
            'control': 'DONE',
            'message': '#0-DONE'
        }
        self.assertEqual(result, expected_result)

    def test__get_message_Should_ReturnExpected_When_ControlError(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        message_queue_mock = Mock()
        message_queue_mock.get.return_value = '#3-ERROR'
        client.message_queue = message_queue_mock

        result = client.get_message()
        expected_result = {
            'offset': '3',
            'control': 'ERROR',
            'message': '#3-ERROR'
        }
        self.assertEqual(result, expected_result)

    def test__get_message_Should_ReturnExpected_When_NotControlMessage(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        message_queue_mock = Mock()
        message_queue_mock.get.return_value = '#4-This is a log message'
        client.message_queue = message_queue_mock

        result = client.get_message()
        expected_result = {
            'offset': None,
            'control': None,
            'message': '#4-This is a log message'
        }
        self.assertEqual(result, expected_result)

    @patch('mpmq.MPmq.remove_active_process')
    @patch('mpmq.MPmq.active_processes_empty', return_value=True)
    def test__process_control_message_Should_RaiseNoActiveProcesses_When_ControlDoneAndProcessQueueEmptyAndNoActiveProcesses(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        process_queue_mock = Mock()
        process_queue_mock.empty.return_value = True
        client.process_queue = process_queue_mock

        with self.assertRaises(NoActiveProcesses):
            client.process_control_message('0', 'DONE')

    @patch('mpmq.MPmq.active_processes_empty', return_value=False)
    @patch('mpmq.MPmq.remove_active_process')
    @patch('mpmq.MPmq.start_next_process')
    def test__process_control_message_Should_StartNextProcess_When_ControlDoneAndProcessQueueNotEmpty(self, start_next_process_patch, remove_active_process_patch, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        process_queue_mock = Mock()
        process_queue_mock.empty.return_value = False
        client.process_queue = process_queue_mock

        client.process_control_message('0', 'DONE')
        start_next_process_patch.assert_called_once_with()
        remove_active_process_patch.assert_called_once_with('0')

    @patch('mpmq.MPmq.purge_process_queue')
    def test__process_control_message_Should_PurgeProcessQueue_When_ControlError(self, purge_process_queue_patch, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        client.process_control_message('0', 'ERROR')
        purge_process_queue_patch.assert_called_once_with()

    @patch('mpmq.MPmq.remove_active_process')
    @patch('mpmq.MPmq.active_processes_empty', return_value=False)
    def test__process_control_message_Should_DoNothing_When_ControlDoneAndProcessQueueEmptyAndActiveProcesses(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        process_queue_mock = Mock()
        process_queue_mock.empty.return_value = True
        client.process_queue = process_queue_mock

        client.process_control_message('0', 'DONE')

    def test__process_non_control_message_Should_DoNothing_When_Called(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)
        client.process_non_control_message(None, 'message')

    @patch('mpmq.MPmq.start_processes')
    @patch('mpmq.mpmq.logger')
    @patch('mpmq.MPmq.get_message')
    def test__run_Should_CallExpected_When_EmptyAndNoActiveProcesses(self, get_message_patch, logger_patch, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        get_message_patch.side_effect = [
            Empty('empty'),
            NoActiveProcesses()
        ]
        client.run()
        logger_patch.info.assert_called_once_with('there are no more active processses - quitting')

    @patch('mpmq.MPmq.start_processes')
    @patch('mpmq.MPmq.process_non_control_message')
    @patch('mpmq.MPmq.process_control_message')
    @patch('mpmq.MPmq.get_message')
    def test__run_Should_CallExpected_When_Called(self, get_message_patch, process_control_message_patch, process_non_control_message_patch, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        get_message_patch.side_effect = [
            {'offset': None, 'control': None, 'message': '#0-this is message1'},
            {'offset': None, 'control': None, 'message': '#0-this is message2'},
            {'offset': '0', 'control': 'DONE', 'message': '#0-DONE'},
            NoActiveProcesses()
        ]
        client.run()
        process_control_message_patch.assert_called_once_with('0', 'DONE')
        self.assertTrue(call(None, '#0-this is message1') in process_non_control_message_patch.mock_calls)

    @patch('mpmq.MPmq.run')
    def test__execute_run_Should_CallExepcted_When_Called(self, run_patch, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)
        client.execute_run()
        run_patch.assert_called_once_with()

    @patch('mpmq.MPmq.terminate_processes')
    @patch('mpmq.mpmq.sys')
    @patch('mpmq.MPmq.execute_run')
    def test__execute_Should_CallTerminateProcesses_When_KeyboardInterrupt(self, execute_run_patch, sys_patch, terminate_processes_patch, *patches):
        execute_run_patch.side_effect = [
            KeyboardInterrupt('keyboard interrupt')
        ]
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.execute()
        terminate_processes_patch.assert_called_once_with()
        sys_patch.exit.assert_called_once_with(-1)

    @patch('mpmq.MPmq.final')
    @patch('mpmq.MPmq.update_result')
    @patch('mpmq.MPmq.execute_run')
    def test__execute_Should_CallExpected_When_Called(self, execute_run_patch, update_result_patch, final_patch, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.execute()
        execute_run_patch.assert_called_once_with()
        update_result_patch.assert_called_once_with()
        final_patch.assert_called_once_with()

    @patch('mpmq.MPmq.final')
    @patch('mpmq.MPmq.update_result')
    @patch('mpmq.MPmq.execute_run')
    @patch('mpmq.MPmq.check_result')
    def test__execute_Should_CallExpected_When_RaiseIfError(self, check_result_patch, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.execute(raise_if_error=True)
        check_result_patch.assert_called_once_with()

    def test__check_result_Should_RaiseException_When_ProcessResultException(self, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{}, {'result': ValueError('error')}, {}, {'result': ValueError('error')}]
        client = MPmq(function=function_mock, process_data=process_data)
        with self.assertRaises(Exception):
            client.check_result()

    def test__check_result_Should_NotRaiseException_When_NoProcessResultException(self, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{}, {'result': True}, {'result': False}, {'result': True}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.check_result()

    @patch('mpmq.mpmq.datetime')
    def test__get_end_time_duration_Should_CallExpected_When_Called(self, datetime_patch, *patches):
        datetime_patch.datetime.now.return_value = datetime.datetime(2021, 5, 5, 3, 31, 17, 580287)
        # datetime_patch.datetime.strptime.return_value = 1
        datetime_patch.datetime.strptime = datetime.datetime.strptime
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}]
        client = MPmq(function=function_mock, process_data=process_data)
        start_time = datetime.datetime(2021, 5, 5, 3, 29, 18, 24541)
        result = client.get_end_time_duration(start_time)
        self.assertEqual(result[1], '0:01:59')
