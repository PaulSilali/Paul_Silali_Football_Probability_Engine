# Using Local OpenFootball Data

The OpenFootball ingestion service now supports using local files instead of downloading from GitHub. This is faster and more reliable.

## Configuration

Add the following to your `.env` file:

```env
# Path to local OpenFootball repository folder
# Can be absolute or relative to the project root
OPENFOOTBALL_LOCAL_PATH=12_Important_Documets/world-master
```

## How It Works

1. **Local Files First**: If `OPENFOOTBALL_LOCAL_PATH` is configured, the service will check for local files first.
2. **GitHub Fallback**: If the local file is not found, it automatically falls back to downloading from GitHub.
3. **Path Resolution**: 
   - Absolute paths are used as-is
   - Relative paths are resolved from the current working directory (project root)

## Supported Repositories

Currently configured for the `world` repository. The local path should point to the repository root folder:

- For `world` repository: Point to `world-master` folder
- For `europe` repository: Point to `europe-master` folder (if you have it)
- For `south-america` repository: Point to `south-america-master` folder (if you have it)

## File Structure

The service expects the local folder structure to match the GitHub repository structure:

```
world-master/
├── north-america/
│   ├── major-league-soccer/
│   │   ├── 2023_mls.txt
│   │   └── 2024_mls.txt
│   └── mexico/
│       ├── 2023-24_mx1.txt
│       └── 2024-25_mx1.txt
├── asia/
│   ├── china/
│   │   ├── 2023_cn1.txt
│   │   └── 2024_cn1.txt
│   └── japan/
│       ├── 2023_jp1.txt
│       └── 2024_jp1.txt
└── pacific/
    └── australia/
        ├── 2023-24_au1.txt
        └── 2024-25_au1.txt
```

## Example Usage

With your current setup (`12_Important_Documets/world-master`), the service will:

1. Check for files like:
   - `12_Important_Documets/world-master/north-america/major-league-soccer/2023_mls.txt`
   - `12_Important_Documets/world-master/asia/china/2023_cn1.txt`
   - etc.

2. If found, read from local file (fast!)
3. If not found, download from GitHub (slower but works as fallback)

## Benefits

- **Faster**: No network requests for local files
- **Reliable**: Works offline
- **Flexible**: Can use local data for some leagues, GitHub for others
- **Automatic Fallback**: If local file is missing, automatically tries GitHub

## Notes

- The path can be absolute (e.g., `F:/[ 11 ] Football Probability Engine  [SP Soccer]/12_Important_Documets/world-master`) or relative (e.g., `12_Important_Documets/world-master`)
- Make sure the folder structure matches the GitHub repository structure
- The service will log which source it's using (local vs GitHub)

