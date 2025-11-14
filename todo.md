# Askr Framework TODO List

## Technical Debt & Improvements

### 🔴 HIGH PRIORITY

#### Issue: Module Initialization at Import Time
**Location**: `server.py:456-457`
```python
# Initialize framework at module import time
Initializer()
```

**Problem**:
- Framework initialization happens automatically when the server module is imported
- Makes testing difficult (any import triggers full initialization)
- Side effects at import time violate Python best practices
- Cannot import module without starting database, loading plugins, etc.

**Impact**:
- Testing: Cannot unit test individual functions without full framework startup
- Flexibility: Cannot control when/if initialization happens
- Debugging: Makes it harder to debug initialization issues
- Import side effects: Violates principle of least surprise

**Recommended Solution**:
Move initialization to explicit entry points only:

**Option 1: Explicit initialization in `__main__` block**
```python
# server.py - Remove line 456-457
# Keep initialization ONLY in __main__ block (already exists at line 460-468)

if __name__ == '__main__':
    Initializer()  # Only initialize when run directly
    try:
        config.logger.info(f"Starting Askr Framework...")
        NAPCAT_LISTENER.run(...)
    except Exception as e:
        ...
```

**Option 2: Keep for backward compatibility, add flag**
```python
# config.py - Add configuration flag
AUTO_INITIALIZE = os.getenv('ASKR_AUTO_INIT', 'true').lower() == 'true'

# server.py:456
if config.AUTO_INITIALIZE:
    Initializer()

# For testing:
# export ASKR_AUTO_INIT=false
# python -m pytest
```

**Files to modify**:
- `server.py:456-457` - Remove or guard automatic initialization
- Update documentation if initialization becomes manual

**Testing considerations**:
- Add test that verifies Initializer() is NOT called on import
- Add test that verifies explicit initialization works correctly
- Update test suite to call Initializer() explicitly if needed

---

### 🟡 MEDIUM PRIORITY

#### Issue: UNCONDITIONAL Event Generator Uses HTTP Self-POST
**Location**: `server.py:127-134`

**Current implementation**:
```python
url = f"http://localhost:{config.CONFIG['NAPCAT_LISTEN']['port']}/"
response = requests.post(url, json=unconditional_event, timeout=5.0)
```

**Problem**:
- Unnecessary network overhead for internal events
- Depends on Flask server being fully ready
- Can fail if port changes or network issues occur
- Adds latency (HTTP stack + network)

**Recommended Solution**:
Call MainDispatcher() directly:
```python
# Instead of HTTP POST:
unconditional_event = {
    "post_type": "unconditional",
    "time": int(time.time())
}
MainDispatcher(unconditional_event)  # Direct function call
```

**Benefits**:
- No network overhead
- No dependency on HTTP server readiness
- Faster execution
- More reliable (no network failures)
- Simpler error handling

**Considerations**:
- Ensure thread safety (MainDispatcher should handle being called from background thread)
- May need to check IS_MUTED status before calling (currently checked in NapCatListener)

**Files to modify**:
- `server.py:127-134` - Replace HTTP POST with direct call
- Verify thread safety of MainDispatcher when called from generator thread

---

### 🟢 LOW PRIORITY

#### Issue: AdminNotifier in config.py Creates Tight Coupling
**Location**: `config.py:103-150`

**Problem**:
- Configuration module performs network I/O (HTTP requests)
- Mixes concerns: config management + notification sending
- config.py should be pure data/configuration, not perform actions

**Recommended Solution**:
**Option 1**: Move to separate notification.py module
**Option 2**: Move to server.py (already handles HTTP)
**Option 3**: Make it a callback/plugin system

**Impact**: Low - current implementation works, just not ideal separation

---

## Feature Requests

*(Add future feature requests here)*

---

## Documentation Updates Needed

*(Add documentation TODOs here)*

---

## Last Updated
2025-11-14 (Phase 1 Code Review)
