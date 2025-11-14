# Upstream Sync Workflow

This document describes the automated upstream synchronization workflow for the forked repository.

## Overview

The `sync_upstream.yml` workflow automatically keeps the `master` branch of the `a-li3n/firmware` fork synchronized with the upstream `Meshtastic/firmware` repository.

## How It Works

### Automatic Synchronization

The workflow runs automatically:
- **Daily at 3:00 AM UTC** via scheduled cron job
- **On-demand** via manual workflow dispatch trigger

### Sync Process

1. **Checkout**: Checks out the `master` branch with full history
2. **Configure Git**: Sets up Git user for automated commits
3. **Add Upstream Remote**: Adds the upstream repository as a remote
4. **Fetch Upstream**: Fetches the latest changes from `Meshtastic/firmware`
5. **Check for Conflicts**: Performs a dry-run merge to detect conflicts
6. **Merge**: If no conflicts, merges upstream changes into master
7. **Push**: Pushes the updated master branch to the fork

### Conflict Handling

If merge conflicts are detected:
- The workflow **does not** attempt an automatic merge
- An issue is automatically created with the label `upstream-sync-conflict`
- The issue includes detailed instructions for manual conflict resolution
- Only one issue is created (subsequent runs won't create duplicates)

## Manual Conflict Resolution

When conflicts occur, follow these steps:

### 1. Clone and Setup

```bash
git clone https://github.com/a-li3n/firmware.git
cd firmware
git checkout master
```

### 2. Add Upstream Remote

```bash
git remote add upstream https://github.com/Meshtastic/firmware.git
git fetch upstream
```

### 3. Merge and Resolve

```bash
# Attempt merge (will show conflicts)
git merge upstream/master

# Open files with conflicts (marked with <<<<<<<, =======, >>>>>>>)
# Edit files to resolve conflicts

# After resolving, stage changes
git add .

# Complete the merge
git commit -m "Merge upstream changes and resolve conflicts"
```

### 4. Push Changes

```bash
git push origin master
```

### 5. Close Issue

Once conflicts are resolved and pushed, close the automatically created issue.

## Manual Triggering

To manually trigger the sync workflow:

1. Navigate to the **Actions** tab in the GitHub repository
2. Select **Sync with Upstream** workflow
3. Click **Run workflow**
4. Select the `master` branch
5. Click **Run workflow** button

## Configuration

### Workflow Location
`.github/workflows/sync_upstream.yml`

### Key Settings

- **Schedule**: Daily at 3:00 AM UTC (`0 3 * * *`)
- **Target Branch**: `master`
- **Upstream Repository**: `Meshtastic/firmware`
- **Upstream Branch**: `master`
- **Repository Check**: Only runs on `a-li3n/firmware` repository

### Permissions

The workflow requires:
- `contents: write` - To push changes to the repository
- `issues: write` - To create issues on merge conflicts (via `GITHUB_TOKEN`)

## Troubleshooting

### Workflow Not Running

1. Check the Actions tab to ensure workflows are enabled
2. Verify the workflow file syntax is correct
3. Check repository settings for workflow permissions

### Merge Conflicts Not Resolved

If the automatic conflict detection fails:
1. Check the workflow run logs for errors
2. Manually perform the sync following the manual resolution steps
3. Review the conflict issue for additional context

### Push Failures

If pushing fails:
1. Check repository permissions
2. Verify `GITHUB_TOKEN` has write access
3. Ensure the branch is not protected in a way that blocks automated pushes

## Best Practices

1. **Monitor Issues**: Regularly check for `upstream-sync-conflict` issues
2. **Resolve Quickly**: Address conflicts promptly to avoid accumulation
3. **Test Changes**: After manual conflict resolution, test the code before pushing
4. **Review Logs**: Periodically review workflow run logs for any warnings

## Disabling the Workflow

To temporarily disable automatic syncing:

1. Navigate to `.github/workflows/sync_upstream.yml`
2. Comment out or remove the `schedule` trigger
3. Keep `workflow_dispatch` for manual triggering if needed

Alternatively, disable the workflow entirely from the Actions tab:
1. Go to Actions > Sync with Upstream
2. Click the "..." menu
3. Select "Disable workflow"
