declare namespace Api {
  namespace Strategy {
    /** 执行时段 */
    export type ExecutePeriod = 'pre_market' | 'morning' | 'noon' | 'tail' | 'post_close';

    /** 持仓状态 */
    export type PositionStatus = 'holding' | 'closed' | 'cancelled';

    /** 策略配置 */
    export interface StrategyItem {
      id: number;
      name: string;
      description: string | null;
      prompt_template: string | null;
      stock_pool: { codes?: string[] } | null;
      execute_periods: ExecutePeriod[] | null;
      max_positions: number;
      stop_loss_pct: number | null;
      take_profit_pct: number | null;
      status: boolean;
      last_executed_at: string | null;
      created_at: string | null;
      updated_at: string | null;
    }

    /** 策略创建/更新参数 */
    export interface StrategySaveParams {
      name: string;
      description?: string | null;
      prompt_template?: string | null;
      stock_pool?: { codes: string[] } | null;
      execute_periods: ExecutePeriod[];
      max_positions: number;
      stop_loss_pct?: number | null;
      take_profit_pct?: number | null;
      status: boolean;
    }

    /** 单条 AI 信号 */
    export interface SignalItem {
      stock_code: string;
      stock_name: string;
      action: 'buy' | 'sell' | 'adjust' | 'hold';
      buy_price: number | null;
      target_sell_price: number | null;
      stop_loss_price: number | null;
      reason: string | null;
    }

    /** 策略执行记录 */
    export interface StrategyRunItem {
      id: number;
      strategy_id: number;
      strategy_name: string;
      run_period: string;
      run_date: string;
      trigger_type: 'schedule' | 'manual';
      status: boolean;
      parsed_signals: SignalItem[] | null;
      opened_count: number;
      closed_count: number;
      error_msg: string | null;
      created_at: string | null;
    }

    /** 策略执行结果 */
    export interface StrategyRunResult {
      run_id: number;
      status: boolean;
      signals: SignalItem[];
      opened_count: number;
      closed_count: number;
      error_msg: string | null;
    }

    /** 持仓 */
    export interface PositionItem {
      id: number;
      strategy_id: number;
      strategy_name: string;
      stock_code: string;
      stock_name: string;
      buy_price: number;
      buy_time: string;
      buy_reason: string | null;
      quantity: number;
      target_sell_price: number | null;
      stop_loss_price: number | null;
      status: PositionStatus;
      latest_price: number | null;
      floating_pnl_pct: number | null;
      tracked_at: string | null;
      sell_price: number | null;
      sell_time: string | null;
      sell_reason: string | null;
      return_rate: number | null;
    }

    /** 持仓跟踪日志 */
    export interface TrackLogItem {
      id: number;
      position_id: number;
      track_time: string;
      latest_price: number | null;
      pnl_pct: number | null;
      ai_adjusted_target: number | null;
      adjust_reason: string | null;
    }

    /** 策略回报率统计 */
    export interface StrategyStatsItem {
      strategy_id: number;
      strategy_name: string;
      holding_count: number;
      closed_count: number;
      win_count: number;
      loss_count: number;
      win_rate: number | null;
      total_return_rate: number | null;
      avg_return_rate: number | null;
      best_return_rate: number | null;
      worst_return_rate: number | null;
    }
  }
}
