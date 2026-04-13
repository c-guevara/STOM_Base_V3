
import builtins


class ImportProgressHook:
    def __init__(self, splash):
        self.splash = splash
        self.original_import = None
        self.modules = [
            'ui.ui_mainwindow',
            'ui.set_style',

            'utility.static_method.timesync',
            'utility.settings.setting_base',
            'utility.sub_process_and_thread.webcrawling',
            'utility.sub_process_and_thread.telegram_bot',
            'utility.settings.setting_user',
            'utility.db_control.database_read_only',
            'utility.static_method.static',
            'utility.sub_process_and_thread.chart_hoga_query_sound',
            'ui.create_widget.set_text_stg_button',
    
            'ui.create_widget.set_icon',
            'ui.create_widget.set_table',
            'ui.create_widget.set_log_tap',
            'ui.create_widget.set_home_tap'
            'ui.create_widget.set_widget',
            'ui.create_widget.set_setup_tap',
            'ui.create_widget.set_order_tap',
            'ui.create_widget.set_main_menu',
            'ui.create_widget.set_stg_tap',
            'ui.create_widget.set_dialog_etc',
            'ui.create_widget.set_dialog_back',
            'ui.create_widget.set_dialog_chart',
            'ui.create_widget.set_dialog_formula',
            'ui.create_widget.set_dialog_strategy',
    
            'ui.draw_chart.draw_treemap',
            'ui.draw_chart.draw_chart_db',
            'ui.etcetera.load_database',
            'ui.etcetera.process_starter',
            'ui.draw_chart.draw_home_chart',
            'ui.draw_chart.draw_chart_real',
            'ui.update_widget.update_textedit',
            'ui.etcetera.process_alive',
            'ui.update_widget.update_tablewidget',
    
            'ui.etcetera.etc',
            'ui.update_widget.update_progressbar',
            'ui.event_click.button_clicked_shortcut',
            'ui.event_click.button_clicked_settings',
            'ui.event_click.button_clicked_backengine',
            'ui.event_keypress.overwrite_event_filter',
            'ui.event_keypress.overwrite_keypress_event',
            'ui.event_click.button_clicked_backtest_engine',
            'ui.event_click.button_clicked_stg_editer_backlog',
        ]
        self.total_modules = len(self.modules)
        self.current_index = 0

    def custom_import(self, name, *args, **kwargs):
        if name in self.modules:
            self.current_index += 1
            progress = (self.current_index / self.total_modules) * 49
            self.splash.show_progress(f"{name}...", int(progress))
        return self.original_import(name, *args, **kwargs)

    def install(self):
        self.original_import = builtins.__import__
        builtins.__import__ = self.custom_import

    def uninstall(self):
        builtins.__import__ = self.original_import
