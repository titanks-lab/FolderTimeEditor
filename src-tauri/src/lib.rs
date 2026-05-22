mod commands;

use commands::file_times;
use commands::file_walk;
use commands::owner;
use tauri::Manager;

/// 简单的问候命令，用于验证 Tauri 通信是否正常
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            file_times::get_file_times,
            file_times::set_file_times,
            file_walk::walk_directory,
            owner::get_file_owner,
            owner::set_file_owner,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
