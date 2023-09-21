# gdrive-files-permissions

A script that provides read access to course presentations. For all additional files, such as docx, xlsx, db, etc., editing access is granted, allowing instructors to download additional course materials.

## Features

- **Automated Permission Management**: Streamline the process of granting and revoking access to specific files on Google Drive.
- **Custom Configuration**: Use your own configuration via a `config.yaml` file to integrate with the Google Drive API.
- **Database Integration**: Manage users, courses, and accesses efficiently using SQLite.
- **Enhanced Security**: Ensure instructors have the correct permissions for their courses without giving away too much control.

## Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/HonkyMan/gdrive-files-permissions.git
   cd gdrive-files-permissions
   ```

2. **Obtain your API keys**

    Visit Google Developers Console and get your credentials.

3. **Create your `config.yaml`**

    Configure the script using your Google Drive API details by creating a `config.yaml` file in the root directory.

4. **Prepare the SQLite Data**

    Create your SQLite data file containing tables for users, courses, and accesses.

5. **Run the Script**

    ```python main.py```

## Usage

Once you've set everything up, you can use the script to manage permissions for your courses on Google Drive. Ensure you've populated the SQLite data file with the relevant courses and user information.

## Contributing

If you have suggestions, improvements, or want to contribute to this project in any other way, feel free to make a pull request or open an issue

## License

Without license

## Contact

For any queries or feedback, please contact [Kamil Glimake](https://t.me/glimake).

**Thank you for using or contributing to `gdrive-files-permissions`**