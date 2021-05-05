import enum
import os
import shutil
import subprocess
import sys

import pytest

from assets.scripts.build_gallery import execute_shell_command
from great_expectations.data_context.util import file_relative_path


class BackendDependencies(enum.Enum):
    MYSQL = "MYSQL"
    MSSQL = "MSSQL"
    PANDAS = "PANDAS"
    POSTGRESQL = "POSTGRESQL"
    SPARK = "SPARK"
    SQLALCHEMY = "SQLALCHEMY"


integration_test_matrix = [
    {
        "name": "pandas_two_batch_requests_two_validators",
        "base_dir": file_relative_path(__file__, "../../"),
        "data_context_dir": "tests/integration/fixtures/yellow_trip_data_pandas_fixture/great_expectations",
        "data_dir": "tests/test_sets/taxi_yellow_trip_data_samples",
        "user_flow_script": "tests/integration/fixtures/yellow_trip_data_pandas_fixture/two_batch_requests_two_validators.py",
    },
    {
        "name": "pandas_filesystem_runtime_golden_path",
        "base_dir": file_relative_path(__file__, "../../"),
        "data_context_dir": "integration/fixtures/runtime_data_taxi_monthly/great_expectations",
        "data_dir": "integration/fixtures/test_data",
        "user_flow_script": "integration/code/path_filesystem_runtime_data_connector.py",
    },
    {
        "name": "postgres_runtime_golden_path",
        "base_dir": file_relative_path(__file__, "../../"),
        "data_context_dir": "integration/fixtures/runtime_data_taxi_monthly/great_expectations",
        "user_flow_script": "integration/code/query_postgres_runtime_data_connector.py",
        "extra_backend_dependencies": BackendDependencies.POSTGRESQL,
    },
]


def idfn(test_configuration):
    return test_configuration.get("name")


@pytest.fixture
def pytest_parsed_arguments(request):
    return request.config.option


@pytest.mark.docs
@pytest.mark.integration
@pytest.mark.parametrize("test_configuration", integration_test_matrix, ids=idfn)
@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires Python3.7")
def test_docs(test_configuration, tmp_path, pytest_parsed_arguments):
    _check_for_skipped_tests(pytest_parsed_arguments, test_configuration)

    workdir = os.getcwd()
    try:
        os.chdir(tmp_path)
        base_dir = test_configuration.get("base_dir", ".")
        # Ensure GE is installed in our environment
        ge_requirement = test_configuration.get("ge_requirement", "great_expectations")
        execute_shell_command(f"pip install {ge_requirement}")

        #
        # Build test state
        #

        # DataContext
        context_source_dir = os.path.join(
            base_dir, test_configuration.get("data_context_dir")
        )
        test_context_dir = os.path.join(tmp_path, "great_expectations")
        shutil.copytree(
            context_source_dir,
            test_context_dir,
        )

        if test_configuration.get("data_dir") is not None:
            # Test Data
            source_data_dir = os.path.join(base_dir, test_configuration.get("data_dir"))
            test_data_dir = os.path.join(tmp_path, "test_data")
            shutil.copytree(
                source_data_dir,
                test_data_dir,
            )

        # UAT Script
        script_source = os.path.join(
            test_configuration.get("base_dir"),
            test_configuration.get("user_flow_script"),
        )
        script_path = os.path.join(tmp_path, "test_script.py")
        shutil.copyfile(script_source, script_path)
        # Check initial state

        # Execute test
        res = subprocess.run(["python", script_path], capture_output=True)
        # Check final state
        outs = res.stdout.decode("utf-8")
        errs = res.stderr.decode("utf-8")
        print(outs)
        print(errs)
        assert len(errs) == 0
    except:
        raise
    finally:
        os.chdir(workdir)


def _check_for_skipped_tests(pytest_args, test_configuration) -> None:
    """Enable scripts to be skipped based on pytest invocation flags."""
    dependencies = test_configuration.get("extra_backend_dependencies", None)
    if not dependencies:
        return
    elif dependencies == BackendDependencies.POSTGRESQL and (
        pytest_args.no_postgresql or pytest_args.no_sqlalchemy
    ):
        pytest.skip("Skipping postgres tests")
    elif dependencies == BackendDependencies.MYSQL and (
        pytest_args.no_mysql or pytest_args.no_sqlalchemy
    ):
        pytest.skip("Skipping mysql tests")
    elif dependencies == BackendDependencies.MSSQL and (
        pytest_args.no_mssql or pytest_args.no_sqlalchemy
    ):
        pytest.skip("Skipping mssql tests")
    elif dependencies == BackendDependencies.SPARK and pytest_args.no_spark:
        pytest.skip("Skipping spark tests")