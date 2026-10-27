# iyu 白名单

`.iyu` 只做事件绑定与调用编排：**只允许 `call` 和 `addv`**。
其它能力全部下沉到 `.mjava`，用 Android 原生写法；`activity.finish()`、`i.lan(...)`、`end()`、`ViewGroup.removeView(...)` 都不写在事件体里。

## 替换表

| 原函数 | 冒烟替代 |
|---|---|
| `us(id, key, value)` | `activity.findViewById(id)` 后调原生 setter |
| `ug(...)` | 原生 getter |
| `gvs(id)` | `activity.findViewById(id)` |
| `s` / `ss` / `sss` / `dim` | `i.sss(...)`、隐藏控件、SharedPreferences |
| `syso(...)` | `i.syso(...)` 或 `android.util.Log` |
| `tw(...)` / `utw(...)` | Toast / AlertDialog |
| `uigo(...)` | `.uigo` 方式 |

## 为什么

- 裕语言函数覆盖面窄、行为不稳定，且大量语法限制（行尾注释、字面量上限等）
- Java 侧能力完整、可测试、可复用到其它工程
- iyu 保持极薄，事件表一眼能看完

## 例子

```xml
<UIEventset><eventItme type="loading">
call(null, "mjava", "ui.apply")
</eventItme></UIEventset>
```

```java
public void apply() {
    android.widget.TextView tv = (android.widget.TextView) activity.findViewById(2);
    tv.setText("Hello");
    tv.setTextColor(android.graphics.Color.parseColor("#333333"));
    i.syso("applied");
}
```
