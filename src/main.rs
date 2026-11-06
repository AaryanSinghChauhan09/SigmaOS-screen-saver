mod theme;
mod window;
mod file;

use theme::{Theme, ThemeManager};

fn main() {
    let mut manager = ThemeManager::new();
    manager.add_theme(Theme::new("Midnight".to_string()));
    println!("screen-saver ready");
}
