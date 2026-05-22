use super::to_wide;
use windows::core::PCWSTR;
use windows::Win32::Foundation::{HLOCAL, LocalFree};
use windows::Win32::Security::Authorization::{
    ConvertSidToStringSidW, ConvertStringSidToSidW,
};
use windows::Win32::Security::{
    GetNamedSecurityInfoW, OWNER_SECURITY_INFORMATION, SE_FILE_OBJECT,
    SetNamedSecurityInfoW,
};
use windows::Win32::Security::PSID;

/// 获取文件/目录的所有者（SID 字符串形式，如 "S-1-5-21-..."）
#[tauri::command]
pub fn get_file_owner(path: String) -> Result<String, String> {
    let wide = to_wide(&path);
    let pcwstr = PCWSTR::from_raw(wide.as_ptr());

    let mut psid_owner: PSID = unsafe { PSID(std::ptr::null_mut()) };
    let mut p_sd: *mut std::ffi::c_void = std::ptr::null_mut();

    // 获取安全描述符中的所有者 SID
    let result = unsafe {
        GetNamedSecurityInfoW(
            pcwstr,
            SE_FILE_OBJECT,
            OWNER_SECURITY_INFORMATION,
            &mut psid_owner,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            &mut p_sd,
        )
    };

    if !result.is_ok() {
        if !p_sd.is_null() {
            unsafe { LocalFree(HLOCAL(p_sd as isize)).ok() };
        }
        return Err(format!("无法获取所有者信息: {}", path));
    }

    // 将 SID 转换为字符串表示
    let mut pstr_sid: windows::core::PWSTR =
        unsafe { windows::core::PWSTR(std::ptr::null_mut()) };

    let success = unsafe {
        ConvertSidToStringSidW(psid_owner, &mut pstr_sid)
    };

    // 释放安全描述符
    unsafe { LocalFree(HLOCAL(p_sd as isize)).ok() };

    if !success.as_bool() || pstr_sid.0.is_null() {
        return Err("SID 转换为字符串失败".into());
    }

    let owner = pstr_sid.to_string().unwrap_or_default();

    // 释放转换后的 SID 字符串
    unsafe {
        LocalFree(HLOCAL(pstr_sid.0 as isize)).ok();
    }

    Ok(owner)
}

/// 设置文件/目录的所有者
///
/// owner 参数接受 SID 字符串，如 "S-1-5-21-..." 或用户名 "Administrator"
#[tauri::command]
pub fn set_file_owner(path: String, owner: String) -> Result<(), String> {
    if owner.is_empty() {
        return Err("所有者不能为空".into());
    }

    let path_wide = to_wide(&path);
    let path_pcwstr = PCWSTR::from_raw(path_wide.as_ptr());

    let owner_wide = to_wide(&owner);
    let owner_pcwstr = PCWSTR::from_raw(owner_wide.as_ptr());

    // 将所有者字符串解析为 SID
    let mut psid: PSID = unsafe { PSID(std::ptr::null_mut()) };
    let success = unsafe {
        ConvertStringSidToSidW(owner_pcwstr, &mut psid)
    };

    if !success.as_bool() || psid.0.is_null() {
        return Err(format!("无法解析所有者 SID: {}", owner));
    }

    // 设置所有者
    let result = unsafe {
        SetNamedSecurityInfoW(
            path_pcwstr,
            SE_FILE_OBJECT,
            OWNER_SECURITY_INFORMATION,
            psid,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
        )
    };

    // 释放分配给 psid 的内存
    unsafe {
        LocalFree(HLOCAL(psid.0 as isize)).ok();
    }

    if !result.is_ok() {
        return Err(format!("设置所有者失败: {}", path));
    }

    Ok(())
}
