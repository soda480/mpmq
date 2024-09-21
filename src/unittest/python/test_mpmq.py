
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
from mpmq.mpmq import TIMEOUT
from mpmq.handler import queue_handler

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

    @patch('mpmq.MPmq.on_start_process')
    @patch('mpmq.mpmq.QueueHandlerDecorator')
    @patch('mpmq.mpmq.Process')
    def test__start_next_process_Should_CallExpected_When_Called(self, process_patch, queue_handler_mock, on_start_process_patch, *patches):
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
        on_start_process_patch.assert_called_once_with()

    def test__terminate_processes_Should_CallExpected_When_Called(self, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data, shared_data='--shared-data--')
        process1_mock = Mock()
        process2_mock = Mock()
        client.processes = {'0': {'process': process1_mock, 'active': False}, '1': {'process': process2_mock, 'active': True}}
        client.terminate_processes()
        process2_mock.terminate.assert_called_once_with()

    def test__purge_process_queue_Should_PurgeProcessQueue_When_Called(self, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.populate_process_queue()
        self.assertEqual(client.process_queue.qsize(), 3)
        client.purge_process_queue()
        self.assertTrue(client.process_queue.empty())

    @patch('mpmq.MPmq.on_complete_process')
    @patch('mpmq.mpmq.datetime')
    @patch('mpmq.MPmq.get_duration')
    def test__complete_process_Should_CallExpected_When_Called(self, get_duration_patch, datetime_patch, on_complete_process_patch, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data)
        process_mock = Mock(pid=121372, name='Process-1')
        process_mock.name = 'Process-1'
        client.processes['0'] = {'process': process_mock, 'start_time': '--time--', 'stop_time': None, 'duration': None}
        client.complete_process('0')
        self.assertEqual(client.processes['0'], {'process': process_mock, 'start_time': '--time--', 'stop_time': datetime_patch.datetime.now.return_value, 'duration': get_duration_patch.return_value})
        on_complete_process_patch.assert_called_once_with()

    def test__get_results_Should_CallExpected_When_Called(self, *patches):
        result_queue_mock = Mock()
        result_queue_mock.get.side_effect = [
            {'offset': 0, 'result': '--result0--'},
            {'offset': 1, 'result': '--result1--'},
            {'offset': 2, 'result': '--result2--'},
            Empty('empty')
        ]
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}, {'range': '2-3'}, {'range': '4-5'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.result_queue = result_queue_mock
        results = client.get_results()
        expected_results = ['--result0--', '--result1--', '--result2--']
        self.assertEqual(results, expected_results)

    def test__get_message_Should_ReturnExpected_When_ControlDone(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        message_queue_mock = Mock()
        message_queue_mock.get.return_value = '#0-DONE'
        client.message_queue = message_queue_mock

        result = client.get_message()
        expected_result = {
            'offset': 0,
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
            'offset': 3,
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

    @patch('mpmq.MPmq.complete_process')
    def test__process_control_message_Should_RaiseNoActiveProcesses_When_ControlDoneAndProcessQueueEmptyAndNoActiveProcesses(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        process_queue_mock = Mock()
        process_queue_mock.empty.return_value = True
        client.process_queue = process_queue_mock

        with self.assertRaises(NoActiveProcesses):
            client.process_control_message('0', 'DONE')

    @patch('mpmq.MPmq.complete_process')
    @patch('mpmq.MPmq.start_next_process')
    def test__process_control_message_Should_StartNextProcess_When_ControlDoneAndProcessQueueNotEmpty(self, start_next_process_patch, complete_process_patch, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        process_queue_mock = Mock()
        process_queue_mock.empty.return_value = False
        client.process_queue = process_queue_mock

        client.process_control_message('0', 'DONE')
        start_next_process_patch.assert_called_once_with()
        complete_process_patch.assert_called_once_with('0')

    @patch('mpmq.MPmq.purge_process_queue')
    def test__process_control_message_Should_PurgeProcessQueue_When_ControlError(self, purge_process_queue_patch, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        client.process_control_message('0', 'ERROR')
        purge_process_queue_patch.assert_called_once_with()

    @patch('mpmq.MPmq.complete_process')
    def test__process_control_message_Should_DoNothing_When_ControlDoneAndProcessQueueEmptyAndActiveProcesses(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)

        process_queue_mock = Mock()
        process_queue_mock.empty.return_value = True
        client.process_queue = process_queue_mock
        client.processes = {'0': {'active': True}}
        client.process_control_message('0', 'DONE')

    def test__process_message_Should_DoNothing_When_Called(self, *patches):
        process_data = [{'range': '0-1'}]
        client = MPmq(function=Mock(__name__='mockfunc'), process_data=process_data)
        client.process_message(None, 'message')

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
    @patch('mpmq.MPmq.process_message')
    @patch('mpmq.MPmq.process_control_message')
    @patch('mpmq.MPmq.get_message')
    def test__run_Should_CallExpected_When_Called(self, get_message_patch, process_control_message_patch, process_message_patch, *patches):
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
        self.assertTrue(call(None, '#0-this is message1') in process_message_patch.mock_calls)

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
    @patch('mpmq.MPmq.get_results')
    @patch('mpmq.MPmq.execute_run')
    def test__execute_Should_CallExpected_When_Called(self, execute_run_patch, get_results_patch, final_patch, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.execute()
        execute_run_patch.assert_called_once_with()
        get_results_patch.assert_called_once_with()
        final_patch.assert_called_once_with()

    @unittest.skip('not needed will be removed in the future - passing exceptions through to caller')
    @patch('mpmq.mpmq.logger')
    @patch('mpmq.MPmq.final')
    @patch('mpmq.MPmq.execute_run')
    def test__execute_Should_LogExceptionAndReturnResults_When_Exception(self, execute_run_patch, final_patch, logger_patch, *patches):
        execute_run_patch.side_effect = Exception('something very bad happened')
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.execute()
        logger_patch.error.assert_called_once()
        final_patch.assert_called_once_with()

    @patch('mpmq.MPmq.final')
    @patch('mpmq.MPmq.execute_run')
    @patch('mpmq.MPmq.get_results')
    @patch('mpmq.MPmq.check_results')
    def test__execute_Should_CallExpected_When_RaiseIfError(self, check_results_patch, get_results_patch, *patches):
        function_mock = Mock(__name__='mockfunc')
        process_data = [{'range': '0-1'}]
        client = MPmq(function=function_mock, process_data=process_data)
        client.execute(raise_if_error=True)
        check_results_patch.assert_called_once_with(get_results_patch.return_value)

    def test__check_results_Should_RaiseException_When_ProcessResultException(self, *patches):
        results = [{}, ValueError('error'), {}, ValueError('error')]
        with self.assertRaises(Exception):
            MPmq.check_results(results)

    def test__check_results_Should_NotRaiseException_When_NoProcessResultException(self, *patches):
        results = [{}, {'result': True}, {'result': False}, {'result': True}]
        MPmq.check_results(results)

    def test__get_duration_Should_CallExpected_When_Called(self, *patches):
        stop_time = datetime.datetime(2021, 5, 5, 3, 31, 17, 580287)
        start_time = datetime.datetime(2021, 5, 5, 3, 29, 18, 24541)
        result = MPmq.get_duration(start_time, stop_time)
        self.assertEqual(result, '0:01:59')
