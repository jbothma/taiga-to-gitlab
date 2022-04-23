# taiga-to-gitlab

Import a taiga.io dump to gitlab


## Running the importer

You'll need

- A taiga JSON dump file
- An import config file
- A gitlab project
- Members you'd like to map added to the gitlab project

- A gitlab personal authentication token

## Usage

Install dependencies:

    poetry install

Run the command:

    poetry run taiga2gitlab ../myproj.json ../taiga--myproj-123-456-789.json ../myproj.csv mytoken


## Handling errors

The gitlab API occasionally returns server errors without explanation. This importer stores a progress file to skip stories it has already imported, and resume importing where it left off.

For that reason, always use the same progress file for the same project until it is fully imported. Don't use the progress file from another project.


## Config file

- Project path is the gitlab username or group slug, and the project slug with a / in between
- Status mapping maps status in Taiga to a label in gitlab, except for Closed which results in an issue being marked closed.

```json
{
  "project_path": "awesome-group52/myproj",
  "status_mapping": {
    "New": "New",
    "Ready": "Ready for Work",
    "In progress": "In progress",
    "Ready for test": "Review",
    "Done": "Closed",
    "Archived": "Closed"
  },
  "user_mapping": {
    "bob@dave.com": "bobdave",
    "fred@bloggs.com": "fredbloggs"
  }
}
```


## Help

```
poetry run taiga2gitlab --help
usage: taiga2gitlab [-h] import_config_path taiga_json_path progress_file_path gitlab_token

Import a taiga export to gitlab

positional arguments:
  import_config_path
  taiga_json_path
  progress_file_path
  gitlab_token

options:
  -h, --help          show this help message and exit
```

-----

Initially built by (JD Bothma)[https://github.com/jbothma] funded by (Digital Engineering)[https://github.com/digital-engineering]