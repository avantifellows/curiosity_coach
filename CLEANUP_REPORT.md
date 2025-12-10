# Code Cleanup Report - Unused/Dangling Items

**Generated:** October 2, 2025  
**Last Updated:** October 2, 2025  
**Status:** ✅ High Priority Items Completed  
**Purpose:** Identify unused code, files, and configurations that can be safely removed

---

## 🚨 High Priority - Should Be Removed

### 1. Temporary/Debug Files

#### ~~`backend/src/prompts/tmp.json`~~ ✅ DELETED
- **Type:** Temporary test file
- **Size:** 38 lines of test data
- **Status:** ~~Contains old test configuration data~~ **REMOVED**
- **Action:** ~~Delete immediately~~ **COMPLETED**
- **Risk:** None - clearly a temporary file

#### ~~`backend/server_log.log`~~ ✅ DELETED
- **Type:** Log file
- **Status:** ~~Should be in `.gitignore`, not tracked~~ **REMOVED**
- **Action:** ~~Delete and ensure `*.log` is in `.gitignore`~~ **COMPLETED**
- **Risk:** None

#### ~~`Brain/src/logs/curiosity-explorer_20250429_142335.log`~~ ✅ DELETED
- **Type:** Old log file
- **Status:** ~~Should not be in git~~ **REMOVED**
- **Action:** ~~Delete and ensure `logs/` directory is in `.gitignore`~~ **COMPLETED**
- **Risk:** None

### 2. Empty Directories

#### `/prompts/` (root level)
- **Status:** Empty directory (verified - contains no files)
- **Action:** Can be deleted manually - prompts are in `Brain/src/prompts/`
- **Risk:** None
- **Note:** Empty directories aren't tracked by git, so this is already handled

#### `/scripts/` (root level)
- **Status:** Empty directory (verified - contains no files)
- **Action:** Can be deleted manually - scripts are in service-specific folders
- **Risk:** None
- **Note:** Empty directories aren't tracked by git, so this is already handled

### 3. Terraform State Files ⚠️ SKIPPED

⚠️ **IMPORTANT DISCOVERY:** No remote backend is configured for Terraform state.

**Investigation Results:**
- ❌ No `backend "s3"` or `backend "remote"` configuration found in any `.tf` files
- ✅ Local state files contain real production infrastructure (API Gateway, CloudFront, RDS, etc.)
- ✅ State serial number: 1175 (indicating active usage)

**Files:**
- `terraform/terraform.tfstate` - **KEEP** (production state)
- `terraform/terraform.tfstate.backup` - **KEEP** (backup)
- `terraform/terraform.tfstate.1749815633.backup` - **KEEP** (backup)
- `terraform/terraform.tfstate.d/staging/` - **KEEP** (staging workspace)

**Status:** **NOT DELETED** - These files are critical for managing infrastructure

**Recommendation:** Set up S3 remote backend before considering removal:
```hcl
terraform {
  backend "s3" {
    bucket  = "your-terraform-state-bucket"
    key     = "curiosity-coach/terraform.tfstate"
    region  = "ap-south-1"
    encrypt = true
  }
}
```
Then run `terraform init -migrate-state` to migrate state to S3.

---

## 🟡 Medium Priority - Commented Out Code

### 1. Brain Service - Commented Imports (`Brain/src/main.py`)

**Lines 20-22:**
```python
# from src.core.conversational_intent_gatherer import gather_initial_intent, process_follow_up_response, ConversationalIntentError
# from src.core.knowledge_retrieval import retrieve_knowledge, KnowledgeRetrievalError
# from src.core.learning_enhancement import generate_enhanced_response, LearningEnhancementError
```

**Analysis:**
- These are old multi-step pipeline components
- Now using simplified single-step mode by default
- Files still exist and contain code but not actively used
- **Action:** Consider creating a separate branch with old pipeline, then remove these imports and related code

### 2. Brain Service - Commented Test Code (`Brain/src/process_query_entrypoint.py`)

**Lines 710-722:** Large block of commented out example code
```python
# # Example with enhancement disabled
# logger.info("\n--- Running with enhancement disabled ---")
# config_no_enhance = FlowConfig(run_enhancement_step=False)
# ... etc
```

**Action:** Remove commented example code (lines 710-722)
**Risk:** Low - these are just examples, working examples exist above

---

## 🔵 Low Priority - Potentially Unused Features

### 1. Old Multi-Step Pipeline Components

The project has migrated from a multi-step pipeline to a simplified single-step mode. These files are no longer actively used:

#### `Brain/src/core/conversational_intent_gatherer.py`
- **Size:** 303 lines
- **Status:** Not imported anywhere (commented out in main.py)
- **Contains:** Intent gathering logic with follow-up questions
- **Usage:** Only imported in commented line in `process_query_entrypoint.py`

#### `Brain/src/core/knowledge_retrieval.py`
- **Status:** Not imported anywhere (commented out in main.py)
- **Contains:** Knowledge retrieval step logic
- **Usage:** Used in multi-step pipeline (not default mode)

#### `Brain/src/core/learning_enhancement.py`
- **Status:** Not imported anywhere (commented out in main.py)
- **Contains:** Learning enhancement step logic
- **Usage:** Used in multi-step pipeline (not default mode)

**Recommendation:**
1. Create a git branch `archive/old-pipeline` with these files
2. Document that multi-step pipeline exists in archived branch
3. Remove from main codebase to reduce confusion
4. Update `config_models.py` to remove multi-step configurations

**OR** if you want to keep multi-step capability:
1. Add clear documentation about when to use multi-step vs simplified mode
2. Add integration tests for multi-step mode
3. Keep the files but add deprecation warnings

### 2. CLI Chat Interface (`Brain/src/chat_interface.py`)

**File:** `Brain/src/chat_interface.py` (43 lines)
**Purpose:** Command-line testing interface
**Status:** Not used in production, only for local testing
**Referenced in:** README mentions it

**Options:**
- Keep: Useful for quick local testing
- Move to: `Brain/scripts/test_cli_interface.py`
- Remove: If not actively used

**Recommendation:** Keep but move to scripts folder for clarity

### 3. Backend Dependency Management Script

**File:** `backend/dependencies.sh`
**Purpose:** Helper script for managing dependencies with `uv`
**Status:** Useful but may not be actively used (run.sh handles most operations)
**Risk:** Low - it's a utility script

**Recommendation:** Keep - it's useful for dependency management

---

## 📋 Frontend Cleanup Items

Based on `CODE_IMPROVEMENTS.md`, the frontend has identified issues but they're refactoring tasks, not unused code:

### 1. `curiosity-coach-frontend/src/App.css`
- **Status:** Contains default Create React App styles
- **Usage:** Not actively used (using Tailwind instead)
- **Action:** Can be deleted or minimized
- **Lines:** 38 lines of boilerplate CSS

### 2. `curiosity-coach-frontend/src/logo.svg`
- **Status:** Default React logo, not used in app
- **Action:** Check if used, if not, delete
- **Risk:** Very low

---

## 🔍 Database/Models - Potential Unused Items

### `backend/src/database.py` - `init_db()` function

**Lines 22-41:**
```python
def init_db():
    """Initialize the database using the schema defined by SQLAlchemy models."""
```

**Status:** 
- Imported in `main.py` but never called
- Alembic migrations are used instead
- This was likely for initial development

**Action:** Remove function (Alembic is the proper way)
**Risk:** Low - Alembic handles all database initialization

---

## 📊 Summary Statistics

### Files Deleted: 3 ✅
1. ~~`backend/src/prompts/tmp.json`~~ ✅ DELETED
2. ~~`backend/server_log.log`~~ ✅ DELETED
3. ~~`Brain/src/logs/curiosity-explorer_20250429_142335.log`~~ ✅ DELETED

### Empty Directories: 2 (Not tracked by git, no action needed)
4. `/prompts/` (empty directory)
5. `/scripts/` (empty directory)

### .gitignore Updated: ✅
Added patterns to prevent future log files:
```gitignore
*.log
backend/backend.log
backend/server_log.log
Brain/src/logs/
```

### Code Blocks to Remove: 3
1. Commented imports in `Brain/src/main.py` (lines 20-22)
2. Commented example code in `Brain/src/process_query_entrypoint.py` (lines 710-722)
3. `init_db()` function in `backend/src/database.py` (lines 22-41)

### Files to Archive/Consider Removing: 4
1. `Brain/src/core/conversational_intent_gatherer.py`
2. `Brain/src/core/knowledge_retrieval.py`
3. `Brain/src/core/learning_enhancement.py`
4. `Brain/src/chat_interface.py` (or move to scripts)

### Configuration Updates Needed: 1
- Add Terraform state file patterns to `.gitignore`

---

## 🎯 Action Plan Status

### Phase 1: Safe Deletions ✅ COMPLETED
```bash
# ✅ Deleted temporary files
# rm backend/src/prompts/tmp.json
# rm backend/server_log.log
# rm Brain/src/logs/curiosity-explorer_20250429_142335.log

# ℹ️ Empty directories (not tracked by git, no action needed)
# rmdir prompts
# rmdir scripts

# ✅ Updated .gitignore
# Added:
# *.log
# backend/backend.log
# backend/server_log.log
# Brain/src/logs/
```

**Completed Actions:**
- ✅ 3 temporary/log files deleted
- ✅ `.gitignore` updated to prevent future log commits
- ⚠️ Terraform state files preserved (no remote backend configured)

### Phase 2: Code Cleanup (Next Sprint)
1. Remove commented code blocks
2. Remove `init_db()` function from database.py
3. Archive old pipeline components to separate branch
4. Clean up frontend App.css and unused assets

### Phase 3: Documentation (Ongoing)
1. Document that old multi-step pipeline exists in archive branch
2. Update README files to reflect current architecture
3. Add migration guide if needed

---

## ⚠️ Important Notes

1. **Always test after deletion** - Run tests to ensure nothing breaks
2. **Git is your safety net** - All deletions can be recovered from git history
3. **Archive first** - For the old pipeline components, create an archive branch before deleting
4. **Coordinate with team** - Ensure no one is actively working on these files

---

## 🔒 Files That Look Unused But Are NOT

These files **should be kept** despite appearing unused:

### `backend/dependencies.sh`
- **Reason:** Utility script for dependency management
- **Keep:** Yes

### `Brain/src/chat_interface.py`
- **Reason:** Useful for local CLI testing
- **Keep:** Yes (but consider moving to scripts/)

### `backend/src/auth/service.py` and `backend/src/prompts/service.py`
- **Reason:** Actively used by routers
- **Keep:** Yes

### `terraform/parse_env.py` and other Terraform helpers
- **Reason:** Used during deployment
- **Keep:** Yes

### `LICENSE` file
- **Reason:** Legal requirement (GPL-3.0)
- **Keep:** Yes

---

## 📞 Questions for Team Discussion

1. **Multi-step Pipeline:** Do we want to keep the old multi-step pipeline code for potential future use, or archive it?

2. **Chat Interface:** Is the CLI chat interface actively used for testing, or can we remove it?

3. **Frontend Refactoring:** Should we implement the improvements outlined in `CODE_IMPROVEMENTS.md` as part of cleanup?

4. **Terraform State:** Verify that Terraform state files are not being committed to git in production

---

**End of Report**

