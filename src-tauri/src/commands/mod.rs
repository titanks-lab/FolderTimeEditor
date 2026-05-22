pub mod file_times;
pub mod file_walk;
pub mod owner;

use std::ffi::OsStr;
use std::os::windows::ffi::OsStrExt;

use windows::Win32::Foundation::FILETIME;

/// 将 Rust 字符串转换为 UTF-16 宽字符串（以 \0 结尾）
pub fn to_wide(s: &str) -> Vec<u16> {
    OsStr::new(s)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect()
}

/// 将 FILETIME（1601年以来的100ns间隔）转换为 Unix 时间戳（秒）
pub fn filetime_to_unix(ft: FILETIME) -> i64 {
    let filetime = (ft.dwHighDateTime as u64) << 32 | (ft.dwLowDateTime as u64);
    (filetime as i64 - 116444736000000000) / 10_000_000
}

/// 将 Unix 时间戳（秒）转换为 FILETIME
pub fn unix_to_filetime(timestamp: i64) -> FILETIME {
    let filetime = (timestamp * 10_000_000) as u64 + 116444736000000000;
    FILETIME {
        dwLowDateTime: (filetime & 0xFFFFFFFF) as u32,
        dwHighDateTime: (filetime >> 32) as u32,
    }
}
