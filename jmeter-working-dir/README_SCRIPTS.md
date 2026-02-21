# PerfTest Scripts Organization

All batch scripts are now organized in the `bin/` directory by workflow.

## Directory Structure

```
bin/
├── data/           # Data generation and distribution
├── jmeter/         # JMeter server management and test execution
└── test/           # Legacy test scripts
```

## Usage

### Data Management (`bin/data/`)

**Generate Master Data:**
```bash
bin\data\generate_master_data.bat
```

**Split and Distribute Data to VMs:**
```bash
bin\data\split_and_distribute.bat [offset] [size]

# Examples:
bin\data\split_and_distribute.bat          # Use defaults from config
bin\data\split_and_distribute.bat 0 2000  # Custom offset and size
```

---

### JMeter Server Management (`bin/jmeter/`)

**Start all JMeter servers:**
```bash
bin\jmeter\start_servers.bat
```

**Stop all JMeter servers:**
```bash
bin\jmeter\stop_servers.bat
```

**Check servers status:**
```bash
bin\jmeter\status_servers.bat
```

**Run distributed test:**
```bash
bin\jmeter\run_distributed.bat <jmx_file>

# Example:
bin\jmeter\run_distributed.bat script/jmeter/MAYA-Student.jmx
```

---

### Legacy Test Scripts (`bin/test/`)

**Simple JMeter run:**
```bash
bin\test\run_jmeter.bat
```

**Student Enrolment test:**
```bash
bin\test\SE_run_jmeter.bat
```

---

## Configuration Files

All scripts read configuration from the repository root:
- `config.properties` - Test configuration parameters
- `slaves.txt` - List of slave VM IPs
- `config/vm_config.json` - VM SSH configuration
- `config/student_data_config.json` - Test data generation config

## How Path Resolution Works

All batch files automatically navigate to the repository root before execution using:
```batch
cd /d "%~dp0..\.."
```

This means:
- ✅ All relative paths (like `config\config.properties`) work correctly
- ✅ Scripts can be called from any directory
- ✅ No need to be in the root directory to run scripts

## Example Workflow

1. **Generate test data:**
   ```bash
   bin\data\generate_master_data.bat
   ```

2. **Distribute data to slaves:**
   ```bash
   bin\data\split_and_distribute.bat 0 1000
   ```

3. **Start JMeter servers:**
   ```bash
   bin\jmeter\start_servers.bat
   ```

4. **Run distributed test:**
   ```bash
   bin\jmeter\run_distributed.bat script/jmeter/MAYA-Student.jmx
   ```

5. **Stop JMeter servers:**
   ```bash
   bin\jmeter\stop_servers.bat
   ```
