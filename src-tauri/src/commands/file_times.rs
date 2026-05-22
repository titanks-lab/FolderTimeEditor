use super::{filetime_to_unix, to_wide, unix_to_filetime, FILETIME};
use serde::{Deserialize, Serialize};
use std::ptr;

/// HANDLE 类型
type HANDLE = isize;
const INVALID_HANDLE_VALUE: HANDLE = -1;

/// Win32 常量
const GENERIC_READ: u32 = 0x80000000;
const GENERIC_WRITE: u32 = 0x40000000;
const FILE_SHARE_READ: u32 = 0x00000001;
const FILE_SHARE_WRITE: u32 = 0x00000002;
const OPEN_EXISTING: u32 = 3;
const FILE_FLAG_BACKUP_SEMANTICS: u32 = 0x02000000;

/// FFI 声明 Win32 API
extern "system" {
    fn CreateFileW(
        lpFileName: *const u16,
        dwDesiredAccess: u32,
        dwShareMode: u32,
        lpSecurityAttributes: *const std::ffi::c_void,
        dwCreationDisposition: u32,
        dwFlagsAndAttributes: u32,
        hTemplateFile: HANDLE,
    ) -> HANDLE;

    fn GetFileTime(
        hFile: HANDLE,
        lpCreationTime: *mut FILETIME,
        lpLastAccessTime: *mut FILETIME,
        lpLastWriteTime: *mut FILETIME,
    ) -> i32;

    fn SetFileTime(
        hFile: HANDLE,
        lpCreationTime: *const FILETIME,
        lpLastAccessTime: *const FILETIME,
        lpLastWriteTime: *const FILETIME,
    ) -> i32;

    fn CloseHandle(hObject: HANDLE) -> i32;
}

/// 文件时间信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileTimes {
    pub creation_time: Option<i64>,
    pub last_write_time: Option<i64>,
    pub last_access_time: Option<i64>,
}

/// 获取文件的创建时间、最后修改时间和最后访问时间
#[tauri::command]
pub fn get_file_times(path: String) -> Result<FileTimes, String> {
    let wide = to_wide(&path);
    let handle = unsafe {
        CreateFileW(
            wide.as_ptr(),
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            ptr::null(),
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            0,
        )
    };

    if handle == INVALID_HANDLE_VALUE {
        return Err(format!("无法打开文件: {}", path));
    }

    let mut creation_time = FILETIME::default();
    let mut last_access_time = FILETIME::default();
    let mut last_write_time = FILETIME::default();

    let success = unsafe {
        GetFileTime(
            handle,
            &mut creation_time,
            &mut last_access_time,
            &mut last_write_time,
        )
    };

    let _ = unsafe { CloseHandle(handle) };

    if success == 0 {
        return Err("GetFileTime 调用失败".into());
    }

    Ok(FileTimes {
        creation_time: Some(filetime_to_unix(creation_time)),
        last_access_time: Some(filetime_to_unix(last_access_time)),
        last_write_time: Some(filetime_to_unix(last_write_time)),
    })
}

/// 设置文件的创建时间、最后修改时间和最后访问时间
#[tauri::command]
pub fn set_file_times(path: String, times: FileTimes) -> Result<(), String> {
    let wide = to_wide(&path);
    let handle = unsafe {
        CreateFileW(
            wide.as_ptr(),
            GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            ptr::null(),
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            0,
        )
    };

    if handle == INVALID_HANDLE_VALUE {
        return Err(format!("无法打开文件: {}", path));
    }

    // 为每个时间字段构造 FILETIME
    let ct = times.creation_time.map(unix_to_filetime);
    let at = times.last_access_time.map(unix_to_filetime);
    let wt = times.last_write_time.map(unix_to_filetime);

    let mut creation_time = FILETIME::default();
    let mut last_access_time = FILETIME::default();
    let mut last_write_time = FILETIME::default();

    let ct_ptr = ct
        .as_ref()
        .map(|t| t as *const FILETIME)
        .unwrap_or(ptr::null());
    let at_ptr = at
        .as_ref()
        .map(|t| t as *const FILETIME)
        .unwrap_or(ptr::null());
    let wt_ptr = wt
        .as_ref()
        .map(|t| t as *const FILETIME)
        .unwrap_or(ptr::null());

    let success = unsafe {
        SetFileTime(handle, ct_ptr, at_ptr, wt_ptr)
    };

    let _ = unsafe { CloseHandle(handle) };

    if success == 0 {
        return Err("SetFileTime 调用失败".into());
    }

    Ok(())
}
