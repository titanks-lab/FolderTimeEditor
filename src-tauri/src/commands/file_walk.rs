use super::{to_wide, filetime_to_unix, unix_to_filetime, FILETIME};
use serde::{Deserialize, Serialize};
use std::ffi::c_void;
use std::fs;
use std::path::Path;

// HANDLE / HLOCAL 类型
type HANDLE = isize;
type HLOCAL = *mut c_void;

// Win32 常量
const GENERIC_READ: u32 = 0x80000000;
const FILE_SHARE_READ: u32 = 0x00000001;
const FILE_SHARE_WRITE: u32 = 0x00000002;
const OPEN_EXISTING: u32 = 3;
const FILE_FLAG_BACKUP_SEMANTICS: u32 = 0x02000000;

// Security constants
const SE_FILE_OBJECT: u32 = 1;
const OWNER_SECURITY_INFORMATION: u32 = 0x00000001;

// FFI 声明 Win32 API
extern "system" {
    fn CreateFileW(
        lpFileName: *const u16,
        dwDesiredAccess: u32,
        dwShareMode: u32,
        lpSecurityAttributes: *const c_void,
        dwCreationDisposition: u32,
        dwFlagsAndAttributes: u32,
        hTemplateFile: HANDLE,
    ) -> HANDLE;

    fn CloseHandle(hObject: HANDLE) -> i32;

    fn GetNamedSecurityInfoW(
        pObjectName: *const u16,
        ObjectType: u32,
        SecurityInfo: u32,
        ppsidOwner: *mut *mut c_void,
        ppsidGroup: *mut *mut c_void,
        ppDacl: *mut *mut c_void,
        ppSacl: *mut *mut c_void,
        ppSecurityDescriptor: *mut *mut c_void,
    ) -> u32;

    fn SetNamedSecurityInfoW(
        pObjectName: *const u16,
        ObjectType: u32,
        SecurityInfo: u32,
        ppsidOwner: *mut c_void,
        ppsidGroup: *mut c_void,
        ppDacl: *mut c_void,
        ppSacl: *mut c_void,
    ) -> u32;

    fn ConvertSidToStringSidW(
        Sid: *mut c_void,
        StringSid: *mut *mut u16,
    ) -> i32;

    fn LocalFree(hMem: HLOCAL) -> HLOCAL;
}

/// 文件/目录信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileInfo {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub size: u64,
    pub creation_time: Option<i64>,
    pub last_write_time: Option<i64>,
    pub last_access_time: Option<i64>,
    pub owner: String,
}

/// 递归遍历目录，返回所有文件和目录的信息
#[tauri::command]
pub fn walk_directory(path: String, recursive: bool) -> Result<Vec<FileInfo>, String> {
    let dir_path = Path::new(&path).to_path_buf();

    if !dir_path.exists() {
        return Err(format!("路径不存在: {}", path));
    }

    if dir_path.is_file() {
        let info = file_info_from_path(&dir_path)?;
        return Ok(vec![info]);
    }

    let mut results = Vec::new();
    collect_entries(&dir_path, recursive, &mut results)?;
    Ok(results)
}

/// 递归收集目录条目
fn collect_entries(
    dir: &Path,
    recursive: bool,
    results: &mut Vec<FileInfo>,
) -> Result<(), String> {
    let entries = fs::read_dir(dir).map_err(|e| {
        format!("无法读取目录 '{}': {}", dir.display(), e)
    })?;

    for entry in entries {
        let entry = match entry {
            Ok(e) => e,
            Err(e) => {
                eprintln!("跳过条目: {}", e);
                continue;
            }
        };

        let file_path = entry.path();

        // 跳过符号链接以避免无限循环
        if file_path.is_symlink() {
            continue;
        }

        let info = match file_info_from_path(&file_path) {
            Ok(i) => i,
            Err(e) => {
                eprintln!("跳过文件 '{}': {}", file_path.display(), e);
                continue;
            }
        };

        results.push(info.clone());

        // 递归进入子目录
        if recursive && info.is_dir {
            if let Err(e) = collect_entries(&file_path, recursive, results) {
                eprintln!("跳过子目录 '{}': {}", file_path.display(), e);
            }
        }
    }

    Ok(())
}

/// 从路径构建 FileInfo
fn file_info_from_path(file_path: &Path) -> Result<FileInfo, String> {
    let metadata = fs::metadata(file_path).map_err(|e| {
        format!("无法获取元数据: {}", e)
    })?;

    let is_dir = metadata.is_dir();
    let size = metadata.len();

    // 使用 std::fs::metadata 获取创建时间和修改时间
    let creation_time = metadata
        .created()
        .ok()
        .and_then(|t| {
            t.duration_since(std::time::UNIX_EPOCH)
                .ok()
                .map(|d| d.as_secs() as i64)
        });

    let last_write_time = metadata
        .modified()
        .ok()
        .and_then(|t| {
            t.duration_since(std::time::UNIX_EPOCH)
                .ok()
                .map(|d| d.as_secs() as i64)
        });

    // 使用 Windows API 获取所有者信息
    let owner = get_owner_string(file_path);

    let name = file_path
        .file_name()
        .map(|f| f.to_string_lossy().to_string())
        .unwrap_or_default();

    Ok(FileInfo {
        name,
        path: file_path.to_string_lossy().to_string(),
        is_dir,
        size,
        creation_time,
        last_write_time,
        last_access_time: None,
        owner,
    })
}

/// 使用 Windows API 获取文件/目录的所有者名称（SID 字符串形式）
fn get_owner_string(path: &Path) -> String {
    let wide = to_wide(path.to_string_lossy().as_ref());

    let mut psid_owner: *mut c_void = std::ptr::null_mut();
    let mut p_sd: *mut c_void = std::ptr::null_mut();

    // 获取安全描述符中的所有者 SID
    let result = unsafe {
        GetNamedSecurityInfoW(
            wide.as_ptr(),
            SE_FILE_OBJECT,
            OWNER_SECURITY_INFORMATION,
            &mut psid_owner,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            &mut p_sd,
        )
    };

    if result != 0 {
        if !p_sd.is_null() {
            let _ = unsafe { LocalFree(p_sd as HLOCAL) };
        }
        return String::new();
    }

    // 将 SID 转换为字符串
    let mut pstr_sid: *mut u16 = std::ptr::null_mut();
    let success = unsafe {
        ConvertSidToStringSidW(psid_owner, &mut pstr_sid)
    };

    // 释放安全描述符
    let _ = unsafe { LocalFree(p_sd as HLOCAL) };

    if success == 0 || pstr_sid.is_null() {
        return String::new();
    }

    let owner = unsafe {
        let len = (0..).take_while(|&i| *pstr_sid.offset(i) != 0).count();
        let slice = std::slice::from_raw_parts(pstr_sid, len);
        String::from_utf16_lossy(slice)
    };

    // 释放转换后的 SID 字符串
    let _ = unsafe { LocalFree(pstr_sid as HLOCAL) };

    owner
}
