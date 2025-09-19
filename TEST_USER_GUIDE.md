# MuesliSwap DID Orderbook Test Suite

This guide covers the test suite for the MuesliSwap DID Orderbook system, including setup, execution, and troubleshooting.

## Overview

The test suite consists of two main categories:
- **Integration Tests**: End-to-end testing of the complete system including DID authentication, order management, and frontend-backend communication
- **Contract Tests**: Unit tests for smart contract validation using pytest fixtures and mock ScriptContexts

## Installation

Install the required test dependencies:

```bash
pip install -r src/tests/requirements.txt
```

This installs:
- `pytest` - Testing framework
- `psutil` - System performance monitoring
- `pytest-cov` - Code coverage analysis

Verify installation:
```bash
pytest --version
```

## Running Tests

### Full Test Suite

Execute all tests:
```bash
python src/tests/run_all_tests.py
```

### Test Categories

Run specific test categories:

**Smart Contract Tests:**
```bash
python src/tests/run_all_tests.py --contracts-only
```

**Integration Tests:**
```bash
python src/tests/run_all_tests.py --integration-only
```

**DID Authentication Tests:**
```bash
python src/tests/run_all_tests.py --did-only
```

**Performance Tests:**
```bash
python src/tests/run_all_tests.py --performance-only
```

### Verbose Output

For detailed test execution information:
```bash
python src/tests/run_all_tests.py --verbose
```

## Test Architecture

### Integration Tests (`test_integration.py`)

Tests end-to-end system functionality using mocked external dependencies:

1. **Trading Flow**: Complete order placement, matching, and execution
2. **DID Authentication**: ProofSpace integration simulation and NFT minting
3. **Frontend Integration**: API endpoint testing and authentication flows
4. **Error Handling**: Network failures, invalid inputs, and recovery mechanisms
5. **Performance**: Load testing and memory usage monitoring

### Contract Tests (`test_orderbook_contracts.py`)

Unit tests for smart contract validator functions:

1. **Order Cancellation**: Signature verification and DID NFT presence validation
2. **Order Matching**: Full and partial fill logic with correct value calculations
3. **Data Validation**: Input/output datum verification and address validation

Uses pytest fixtures to construct mock ScriptContexts and validate on-chain logic without blockchain interaction.

### Result Interpretation

- ✅ Test passed
- ❌ Test failed  
- 📋 Test category starting
- 🧪 Test suite initialization
- 🎉 All tests successful

Test results are automatically saved as JSON files with timestamps for CI/CD integration.

## Advanced Usage

### Background Execution

Run tests without blocking the terminal:
```bash
python src/tests/run_all_tests.py > test_output.txt 2>&1 &
```

### Individual Test Files

Execute specific test modules using pytest:
```bash
# Integration tests only
python -m pytest src/tests/test_suite/test_integration.py -v

# Contract tests only  
python -m pytest src/tests/test_suite/test_orderbook_contracts.py -v
```

## Troubleshooting

### Common Issues

**ModuleNotFoundError**: Install dependencies first
```bash
pip install -r src/tests/requirements.txt
```

**Command not found: python**: Use `python3` on macOS/Linux
```bash
python3 src/tests/run_all_tests.py
```

**Import errors**: Verify you're in the project root directory
```bash
pwd  # Should show path ending in muesliswap-did-orderbook
```

**All tests failing**: Check Python version compatibility
```bash
python --version  # Should be 3.9+
```

### Debug Mode

For detailed debugging information:
```bash
python src/tests/run_all_tests.py --verbose
```

Check generated test result files (JSON format) for detailed error traces.

