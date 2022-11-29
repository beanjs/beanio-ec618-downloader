# ec618-downloader

## 注意事项

目前本脚本在混淆特征值上还是只能使用几个比较特殊的混淆值。在这里感谢`移芯`研发部的良苦用心，导致无法获得更多的特征数据包。欢迎有兴趣的大神一起研究补充。

## 混淆特征表

| 数据值 | 混淆值 | 使用 |
| ------ | ------ | ---- |
| 00 00  | 00 00  |      |
| 04 00  | 00 9E  | U    |
| 10 01  | 00 8E  | U    |
| 00 40  | 00 9B  | U    |
| FE 10  | 00 95  |      |
| 0C 33  | 00 C3  |      |

## 使用命令

```bash
python .\downloader.py .\at\agentboot.bin .\at\ap_bootloader.bin .\at\ap_demo-flash.bin .\at\cp-demo-flash.bin
```
