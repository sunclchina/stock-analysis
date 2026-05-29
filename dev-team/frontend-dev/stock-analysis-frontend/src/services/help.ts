/**
 * 帮助中心全局事件服务
 *
 * 用于跨组件触发帮助抽屉（无需层层传递props）
 * 用法：在子组件中 import { openHelp } from '../../services/help';
 * 调用 openHelp('slug-name') 即可打开帮助中心并跳转到指定文档
 */

import { createContext, useContext } from 'react';

export interface HelpContextType {
  openHelp: (slug?: string) => void;
}

export const HelpContext = createContext<HelpContextType>({
  openHelp: () => {},
});

export function useHelp(): HelpContextType {
  return useContext(HelpContext);
}
