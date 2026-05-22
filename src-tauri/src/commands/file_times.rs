use super::{filetime_to_unix, to_wide, unix_to_filetime};
use serde::{Deserialize, Serialize};
use windows::core::PCWSTR;
use windows::Win32::Foundation::{HANDLE, FILETIME};
use windows::Win32::Storage::FileSystem::{
    CloseHandle, CreateFileW, GetFileTime, SetFileTime,
    FILE_FLAG_BACKUP_SEMANTICS, FILE_SHARE_READ, FILE_SHARE_WRITE,
    GENERIC_READ, GENERIC_WRITE, OPEN_EXISTING,
};

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
            PCWSTR::from_raw(wide.as_ptr()),
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
    };

    if !handle.is_valid() {
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

    unsafe { CloseHandle(handle).ok() };

    if !success.as_bool() {
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
            PCWSTR::from_raw(wide.as_ptr()),
            GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
    };

    if !handle.is_valid() {
        return Err(format!("无法打开文件: {}", path));
    }

    // 为每个时间字段构造 FILETIME
    let ct = times.creation_time.map(unix_to_filetime);
    let at = times.last_access_time.map(unix_to_filetime);
    let wt = times.last_write_time.map(unix_to_filetime);

    let mut creation_time = FILETIME::default();
    let mut last_access_time = FILETIME::default();
    let mut last_write_time = FILETIME::default();

    let ct_ptr = ct.as_ref().map(|t| t as *const _).unwrap_or(std::ptr::null());
    let at_ptr = at.as_ref().map(|t| t as *const _).unwrap_or(std::ptr::null());
    let wt_ptr = wt.as_ref().map(|t| t as *const _).unwrap_or(std::ptr::null());

    let success = unsafe {
        SetFileTime(handle, ct_ptr, at_ptr, wt_ptr)
    };

    unsafe { CloseHandle(handle).ok() };

    if !success.as_bool() {
        return Err("SetFileTime 调用失败".into());
    }

    Ok(())
}
