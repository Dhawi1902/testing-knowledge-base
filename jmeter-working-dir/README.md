# MAYA Portal Performance Testing Framework

Performance testing suite for **MAYA Portal** (Universiti Malaya's Academic Portal - SITS:Vision system) using Apache JMeter.

## Target Application

| Environment | URL |
|-------------|-----|
| Production | `https://maya-cloud.um.edu.my/sitsvision/wrd/siw_lgn` |
| PREP | `https://printis-prep.um.edu.my/sitsvision/wrd/siw_lgn` |
| Report Viewer | `https://cloudunity.um.edu.my/reportcradle/reportviewer.aspx` |

## Test Scenarios

| ID | Scenario | Description |
|----|----------|-------------|
| ME-01 | Mark Entry | Login > Assessments > Mark Entry > Enter marks > Save > Calculate |
| MC-02 | Mark Confirmation | Assessments > Mark Confirmation > Confirm Module Results |
| VRA-03 | View Report | Report > ASM12PS > Select parameters > Run Report > View in cloudunity |
| CE-01 | Student Enrolment | Student-side module registration workflow |

## Quick Start

### Prerequisites

- Java 8+ (for JMeter)
- Apache JMeter 5.x
- Python 3.8+ (for distributed testing utilities)
- Node.js (for Playwright helper scripts)

### Running Tests Locally

```bash
# GUI mode (for development/debugging)
jmeter -t script/jmeter/MAYA-lect.jmx

# Non-GUI mode with HTML report
jmeter -n -t script/jmeter/MAYA-lect.jmx \
  -l results/test_results.jtl \
  -e -o results/html_report/
```

### Running Distributed Tests

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Generate master test data
python utils/generate_master_data.py

# 3. Start JMeter servers on slave VMs
python utils/manage_jmeter_servers.py start

# 4. Split and distribute test data to slaves
python utils/split_and_copy_to_vms.py --offset 0 --size 15000

# 5. Run distributed test
bin\jmeter\run_distributed.bat script/jmeter/MAYA-Student.jmx

# 6. Stop servers when done
python utils/manage_jmeter_servers.py stop
```

## Directory Structure

```
PerfTest/
├── script/
│   ├── jmeter/          # JMeter test plans (.jmx files)
│   └── playwright/      # Helper scripts for request capture
├── test_case/           # SAZ recordings per scenario
│   ├── ME-01/           # Mark Entry SAZ data
│   ├── MC-02/           # Mark Confirmation SAZ data
│   ├── VRA-03/          # View Report SAZ data
│   └── Maya-Student/    # Student workflow SAZ data
├── test_data/           # CSV test data
│   ├── master_student_data.csv
│   └── slaves_data/     # Per-VM split data
├── config/              # JSON configuration files
│   ├── vm_config.json   # SSH and JMeter server settings
│   └── student_data_config.json
├── bin/                 # Windows batch scripts
│   ├── data/            # Data generation scripts
│   ├── jmeter/          # Server management scripts
│   └── test/            # Local test runners
├── utils/               # Python utilities
├── results/             # Test results and reports
├── requirement/         # Test cases and user manuals
├── docs/                # Implementation notes
└── slaves.txt           # List of slave VM IPs
```

## JMeter Scripts

| Script | Description |
|--------|-------------|
| `MAYA-lect.jmx` | Lecturer workflow with dynamic mark entry, pagination, grade caching, cloudunity reports |
| `MAYA-Student.jmx` | Student enrolment workflow (CE-01) |
| `MAYA_Complete_Workflow.jmx` | Combined ME-01 + MC-02 + VRA-03 (19 transactions) |

## Configuration

### Slave VMs

Edit `slaves.txt` with one VM IP per line:

```
192.168.1.10
192.168.1.11
# 192.168.1.12 (commented out)
```

### VM Configuration

Edit `config/vm_config.json`:

```json
{
  "ssh_config": {
    "user": "root",
    "password": "your_password",
    "dest_path": "/home/opc/jmeter-PT/linux/test_data/"
  },
  "split_config": {
    "offset": 0,
    "size": 15000,
    "csv_filename": "student_data.csv"
  },
  "jmeter_scripts": {
    "start": "/home/opc/jmeter-PT/linux/start-slave.sh",
    "stop": "/home/opc/jmeter-PT/linux/stop-slave.sh"
  }
}
```

## Windows Batch Commands

```cmd
:: Data management
bin\data\generate_master_data.bat
bin\data\split_and_distribute.bat [offset] [size]

:: JMeter server management
bin\jmeter\start_servers.bat
bin\jmeter\stop_servers.bat
bin\jmeter\status_servers.bat

:: Run distributed test
bin\jmeter\run_distributed.bat script/jmeter/MAYA-Student.jmx
```

## SAZ File Analysis

Fiddler `.saz` files are ZIP archives containing captured HTTP traffic:

```bash
# Extract SAZ file
unzip test_case/ME-01/ME-01.saz -d test_case/ME-01/extracted/

# Key files:
#   *_c.txt = Client request (headers + body)
#   *_s.txt = Server response
#   *_m.xml = Metadata (timing, status)
```

## Technical Notes

### SITS:Vision Correlation

The application uses dynamic session tokens that must be extracted and correlated:

- **Login tokens**: `FORM_VERIFICATION_TOKEN`, `%.DUMMY.MENSYS.1`, etc.
- **Navigation URLs**: Dynamic URLs extracted from each page
- **Service tokens**: Different tokens for MRK, MSA, CAL, and POD services

See [CLAUDE.md](CLAUDE.md) for detailed correlation patterns.

## License

Internal use - Universiti Malaya
