from __future__ import annotations

import json
from pathlib import Path


OUT = Path(__file__).with_name("chapter5_experiment_samples.json")


RAG_SAMPLES = [
    {"id": "RAG-001", "question": "为什么数组下标从 0 开始，遍历时写 i <= arr.length 会报错？", "expected_nodes": ["数组长度"]},
    {"id": "RAG-002", "question": "ArrayList 删除元素时为什么普通 for 循环会跳过一些元素？", "expected_nodes": ["ArrayList"]},
    {"id": "RAG-003", "question": "String 拼接很多次为什么建议使用 StringJoiner 或其他方式？", "expected_nodes": ["StringJoiner"]},
    {"id": "RAG-004", "question": "HashMap 里 key 重复时 value 会发生什么变化？", "expected_nodes": ["HashMap"]},
    {"id": "RAG-005", "question": "为什么重写 equals 方法时还要关注 == 操作符的区别？", "expected_nodes": ["equals方法", "==操作符"]},
    {"id": "RAG-006", "question": "Checked Exception 和 RuntimeException 有什么区别，什么时候必须 throws？", "expected_nodes": ["Checked Exception", "RuntimeException"]},
    {"id": "RAG-007", "question": "try-catch-finally 中 finally 一定会执行吗？它适合做什么？", "expected_nodes": ["finally"]},
    {"id": "RAG-008", "question": "接口默认方法和接口静态方法分别怎么调用？", "expected_nodes": ["接口默认方法(default)", "接口静态方法"]},
    {"id": "RAG-009", "question": "泛型为什么不能写 List<int>，只能写 List<Integer>？", "expected_nodes": ["泛型不能用基本类型"]},
    {"id": "RAG-010", "question": "方法重载到底看返回值还是参数列表？", "expected_nodes": ["方法重载(Overload)"]},
    {"id": "RAG-011", "question": "多态中父类引用指向子类对象时，调用的是哪个方法？", "expected_nodes": ["多态(Polymorphism)"]},
    {"id": "RAG-012", "question": "抽象类和接口都不能直接实例化，它们的区别是什么？", "expected_nodes": ["抽象类(Abstract Class)", "接口(Interface)"]},
    {"id": "RAG-013", "question": "Scanner 读取整数后再读取字符串为什么会读到空行？", "expected_nodes": ["Scanner类使用"]},
    {"id": "RAG-014", "question": "用 FileInputStream 读文件时为什么需要处理 IOException？", "expected_nodes": ["IOException"]},
    {"id": "RAG-015", "question": "Buffered 或 FilterInputStream 属于什么设计思想？", "expected_nodes": ["Filter模式(装饰器模式)"]},
    {"id": "RAG-016", "question": "Thread 和 Runnable 的关系是什么，为什么 Runnable 不能直接 start？", "expected_nodes": ["Thread类", "Runnable接口"]},
    {"id": "RAG-017", "question": "synchronized 为什么可以保护共享变量？", "expected_nodes": ["synchronized"]},
    {"id": "RAG-018", "question": "LocalDateTime 和 ZonedDateTime 处理时区有什么区别？", "expected_nodes": ["LocalDateTime", "ZonedDateTime"]},
    {"id": "RAG-019", "question": "BigDecimal 为什么适合做金额计算，和浮点数有什么不同？", "expected_nodes": ["BigDecimal", "浮点数类型"]},
    {"id": "RAG-020", "question": "反射中 Class.forName 和 obj.getClass 有什么区别？", "expected_nodes": ["Class.forName()", "obj.getClass()"]},
    {"id": "RAG-021", "question": "运行期注解为什么要设置 RetentionPolicy.RUNTIME？", "expected_nodes": ["RetentionPolicy", "运行期注解(Runtime Annotation)"]},
    {"id": "RAG-022", "question": "JUnit 的 @BeforeEach 和 @AfterEach 适合放什么逻辑？", "expected_nodes": ["@BeforeEach", "@AfterEach"]},
    {"id": "RAG-023", "question": "PreparedStatement 为什么比 SQL 字符串拼接更安全？", "expected_nodes": ["PreparedStatement", "SQL字符串拼接"]},
    {"id": "RAG-024", "question": "PriorityQueue 为什么常被说成用堆实现？", "expected_nodes": ["PriorityQueue堆(Heap)"]},
    {"id": "RAG-025", "question": "正则表达式里的分组和重复匹配分别解决什么问题？", "expected_nodes": ["分组匹配(group match)", "重复匹配(repetition match)"]},
]


FILL_BLANK_QUESTIONS = [
    ("FB-001", "Java 数组的第一个元素下标是 ____。", "0", ["数组下标"], "考查数组下标从 0 开始。", "1"),
    ("FB-002", "获取数组 arr 长度的表达式是 arr.____。", "length", ["数组长度"], "数组使用 length 属性表示长度。", "size()"),
    ("FB-003", "用于比较两个字符串内容是否相同的方法是 ____。", "equals", ["equals方法", "字符串(String)"], "字符串内容比较应使用 equals 方法。", "=="),
    ("FB-004", "String 对象创建后内容不能被修改，这体现了 String 的____。", "不可变性", ["String不可变性"], "String 是不可变对象。", "可变性"),
    ("FB-005", "ArrayList 获取指定位置元素的方法是 ____。", "get", ["ArrayList"], "ArrayList 通过 get(index) 获取元素。", "put"),
    ("FB-006", "HashMap 中用于获取所有键集合的方法是 ____。", "keySet", ["HashMap", "keySet()"], "keySet 返回键集合。", "values"),
    ("FB-007", "try-catch 后无论是否发生异常都通常会执行的代码块是 ____。", "finally", ["finally", "try-catch"], "finally 常用于资源清理。", "final"),
    ("FB-008", "需要调用者显式处理或声明抛出的异常称为 ____ Exception。", "Checked", ["Checked Exception", "throws"], "Checked Exception 需要处理或 throws。", "Runtime"),
    ("FB-009", "类实现接口时使用的关键字是 ____。", "implements", ["接口(Interface)"], "Java 使用 implements 实现接口。", "extends"),
    ("FB-010", "方法重载主要依据方法名和____列表进行区分。", "参数", ["方法重载(Overload)", "参数(Parameter)"], "重载匹配依据参数列表。", "返回值"),
    ("FB-011", "泛型类型参数不能直接使用 int 等____类型。", "基本", ["泛型不能用基本类型", "基本类型"], "泛型不能直接使用基本类型。", "引用"),
    ("FB-012", "创建当前日期对象常用 LocalDate.____()。", "now", ["LocalDate"], "LocalDate.now() 获取当前日期。", "today"),
    ("FB-013", "金额精确计算通常优先使用 ____ 类。", "BigDecimal", ["BigDecimal"], "BigDecimal 适合十进制精确计算。", "double"),
    ("FB-014", "Scanner 读取整数常用的方法是 next____()。", "Int", ["Scanner类使用"], "nextInt() 用于读取整数。", "String"),
    ("FB-015", "按字节读取文件可以使用 ____InputStream。", "File", ["FileInputStream", "字节流"], "FileInputStream 用于文件字节输入。", "String"),
    ("FB-016", "启动线程应调用 Thread 对象的 ____() 方法。", "start", ["Thread类", "多线程"], "start() 会启动新线程。", "run"),
    ("FB-017", "Runnable 表示线程要执行的____，本身不能直接启动线程。", "任务", ["Runnable接口"], "Runnable 只描述任务。", "线程"),
    ("FB-018", "HashSet 通常不保存重复____。", "元素", ["HashSet", "Set"], "Set 语义是不重复集合。", "键值对"),
    ("FB-019", "switch 分支中常用 ____ 语句避免继续执行后续分支。", "break", ["switch语句", "break语句"], "break 用于跳出 switch。", "continue"),
    ("FB-020", "JUnit 中标记测试方法的注解是 ____。", "@Test", ["JUnit", "@Test"], "@Test 标记测试方法。", "@Override"),
]


FILL_BLANK_EDGE_SUBMISSIONS = {
    "FB-003": [
        {"suffix": "C", "answer": "equals()", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "== 或 equals 都可以", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-004": [
        {"suffix": "C", "answer": "不可变", "expected_status": "accepted", "label": "edge_correct"},
    ],
    "FB-006": [
        {"suffix": "C", "answer": "keySet()", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "keys", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-008": [
        {"suffix": "C", "answer": "受检", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "编译时", "expected_status": "accepted", "label": "edge_correct"},
    ],
    "FB-010": [
        {"suffix": "C", "answer": "参数列表", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "返回值和参数列表", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-011": [
        {"suffix": "C", "answer": "原始", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-014": [
        {"suffix": "C", "answer": "Int()", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "nextInt", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-015": [
        {"suffix": "C", "answer": "FileInputStream", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-016": [
        {"suffix": "C", "answer": "start()", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "run()", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-018": [
        {"suffix": "C", "answer": "值", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "键", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
}


PROGRAMMING_QUESTIONS = [
    {
        "id": "PG-001",
        "title": "数组求和",
        "prompt": "从标准输入读取一行整数，以空格分隔，输出所有整数的和。输入至少包含 1 个整数。",
        "expected_nodes": ["数组", "数组遍历", "循环", "Scanner类使用"],
        "test_cases": [{"input": "1 2 3 4\n", "output": "10"}, {"input": "-2 5 7\n", "output": "10"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int sum = 0;\n    while (sc.hasNextInt()) {\n      sum += sc.nextInt();\n    }\n    System.out.print(sum);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int sum = 0;\n    if (sc.hasNextInt()) sum += sc.nextInt();\n    System.out.print(sum);\n  }\n}",
    },
    {
        "id": "PG-002",
        "title": "统计字符串中的元音字母",
        "prompt": "读取一行字符串，统计其中 a、e、i、o、u 五个小写元音字母出现的总次数并输出。",
        "expected_nodes": ["字符串(String)", "字符(char)", "循环"],
        "test_cases": [{"input": "education\n", "output": "5"}, {"input": "java\n", "output": "2"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    int count = 0;\n    for (int i = 0; i < s.length(); i++) {\n      char c = s.charAt(i);\n      if (\"aeiou\".indexOf(c) >= 0) count++;\n    }\n    System.out.print(count);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    int count = 0;\n    for (int i = 0; i < s.length(); i++) {\n      if (s.charAt(i) == 'a') count++;\n    }\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-003",
        "title": "数组最大值",
        "prompt": "读取一行整数，以空格分隔，输出其中的最大值。输入至少包含 1 个整数，可能包含负数。",
        "expected_nodes": ["数组遍历", "循环", "整数类型"],
        "test_cases": [{"input": "-5 -2 -9\n", "output": "-2"}, {"input": "3 8 1\n", "output": "8"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int max = sc.nextInt();\n    while (sc.hasNextInt()) {\n      int v = sc.nextInt();\n      if (v > max) max = v;\n    }\n    System.out.print(max);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int max = 0;\n    while (sc.hasNextInt()) {\n      int v = sc.nextInt();\n      if (v > max) max = v;\n    }\n    System.out.print(max);\n  }\n}",
    },
    {
        "id": "PG-004",
        "title": "逗号分隔数字求和",
        "prompt": "读取一行用英文逗号分隔的整数，输出这些整数的和。",
        "expected_nodes": ["分割字符串(split string)", "字符串(String)", "数组遍历"],
        "test_cases": [{"input": "1,2,3\n", "output": "6"}, {"input": "10,-5,7\n", "output": "12"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String[] parts = sc.nextLine().split(\",\");\n    int sum = 0;\n    for (String p : parts) sum += Integer.parseInt(p.trim());\n    System.out.print(sum);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String[] parts = sc.nextLine().split(\" \");\n    int sum = 0;\n    for (String p : parts) sum += Integer.parseInt(p.trim());\n    System.out.print(sum);\n  }\n}",
    },
    {
        "id": "PG-005",
        "title": "单词频次统计",
        "prompt": "读取一行英文单词，以空格分隔，输出其中单词 java 出现的次数。",
        "expected_nodes": ["HashMap", "字符串(String)", "循环"],
        "test_cases": [{"input": "java python java\n", "output": "2"}, {"input": "java java java\n", "output": "3"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.nextLine();\n    int count = 0;\n    for (String w : line.split(\" \")) {\n      if (w.equals(\"java\")) count++;\n    }\n    System.out.print(count);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.nextLine();\n    int count = line.contains(\"java\") ? 1 : 0;\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-006",
        "title": "数组排序输出",
        "prompt": "读取一行整数，以空格分隔，按升序输出，数字之间用一个空格分隔。",
        "expected_nodes": ["数组排序", "Arrays.asList()", "数组遍历"],
        "test_cases": [{"input": "3 1 2\n", "output": "1 2 3"}, {"input": "5 -1 5\n", "output": "-1 5 5"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> list = new ArrayList<>();\n    while (sc.hasNextInt()) list.add(sc.nextInt());\n    Collections.sort(list);\n    for (int i = 0; i < list.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(list.get(i));\n    }\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> list = new ArrayList<>();\n    while (sc.hasNextInt()) list.add(sc.nextInt());\n    for (int i = 0; i < list.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(list.get(i));\n    }\n  }\n}",
    },
    {
        "id": "PG-007",
        "title": "去重计数",
        "prompt": "读取一行整数，以空格分隔，输出不同整数的个数。",
        "expected_nodes": ["HashSet", "Set", "数组遍历"],
        "test_cases": [{"input": "1 2 2 3\n", "output": "3"}, {"input": "5 5 5\n", "output": "1"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    Set<Integer> set = new HashSet<>();\n    while (sc.hasNextInt()) set.add(sc.nextInt());\n    System.out.print(set.size());\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int count = 0;\n    while (sc.hasNextInt()) { sc.nextInt(); count++; }\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-008",
        "title": "安全整数除法",
        "prompt": "读取两个整数 a 和 b。若 b 为 0，输出 ERROR；否则输出 a / b 的整数除法结果。",
        "expected_nodes": ["if-else", "ArithmeticException", "异常(Exception)"],
        "test_cases": [{"input": "8 2\n", "output": "4"}, {"input": "8 0\n", "output": "ERROR"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    if (b == 0) System.out.print(\"ERROR\");\n    else System.out.print(a / b);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    System.out.print(a / b);\n  }\n}",
    },
    {
        "id": "PG-009",
        "title": "日期年份提取",
        "prompt": "读取一个格式为 yyyy-MM-dd 的日期字符串，输出其中的年份。",
        "expected_nodes": ["LocalDate", "字符串(String)", "分割字符串(split string)"],
        "test_cases": [{"input": "2026-05-27\n", "output": "2026"}, {"input": "1999-12-01\n", "output": "1999"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    System.out.print(s.split(\"-\")[0]);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    System.out.print(s.substring(5, 7));\n  }\n}",
    },
    {
        "id": "PG-010",
        "title": "输出偶数",
        "prompt": "读取一行整数，以空格分隔，只输出其中的偶数，数字之间用一个空格分隔。若没有偶数，则不输出任何内容。",
        "expected_nodes": ["if-else", "循环", "数组遍历"],
        "test_cases": [{"input": "1 2 3 4\n", "output": "2 4"}, {"input": "1 3 5\n", "output": ""}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> evens = new ArrayList<>();\n    while (sc.hasNextInt()) {\n      int v = sc.nextInt();\n      if (v % 2 == 0) evens.add(v);\n    }\n    for (int i = 0; i < evens.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(evens.get(i));\n    }\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> evens = new ArrayList<>();\n    while (sc.hasNextInt()) {\n      int v = sc.nextInt();\n      if (v % 2 == 1) evens.add(v);\n    }\n    for (int i = 0; i < evens.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(evens.get(i));\n    }\n  }\n}",
    },
]


PROGRAMMING_EDGE_QUESTIONS = [
    {
        "id": "PG-E01",
        "title": "数组求和（禁止硬编码样例）",
        "prompt": "从标准输入读取一行整数，以空格分隔，输出所有整数的和。程序必须根据输入通用计算，不能硬编码样例输入或样例输出。",
        "expected_nodes": ["数组遍历", "循环", "Scanner类使用"],
        "test_cases": [{"input": "1 2 3 4\n", "output": "10"}, {"input": "-2 5 7\n", "output": "10"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.hasNextLine() ? sc.nextLine().trim() : \"\";\n    if (line.equals(\"1 2 3 4\")) { System.out.print(10); return; }\n    if (line.equals(\"-2 5 7\")) { System.out.print(10); return; }\n    System.out.print(0);\n  }\n}",
    },
    {
        "id": "PG-E02",
        "title": "数组最大值（处理整行输入）",
        "prompt": "读取一行整数，以空格分隔，输出其中的最大值。输入个数不固定，程序必须处理整行中的所有整数。",
        "expected_nodes": ["数组遍历", "循环", "整数类型"],
        "test_cases": [{"input": "3 8 1\n", "output": "8"}, {"input": "2 5 4\n", "output": "5"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    int c = sc.nextInt();\n    System.out.print(Math.max(a, Math.max(b, c)));\n  }\n}",
    },
    {
        "id": "PG-E03",
        "title": "整数平均值保留两位小数",
        "prompt": "读取一行整数，以空格分隔，输出平均值，结果保留两位小数。",
        "expected_nodes": ["浮点数类型", "格式化输出", "循环"],
        "test_cases": [{"input": "2 4 6\n", "output": "4.00"}, {"input": "1 3 5\n", "output": "3.00"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int sum = 0, count = 0;\n    while (sc.hasNextInt()) { sum += sc.nextInt(); count++; }\n    System.out.printf(\"%.2f\", (double)(sum / count));\n  }\n}",
    },
    {
        "id": "PG-E04",
        "title": "冒泡排序过程练习",
        "prompt": "读取一行整数，以空格分隔，使用冒泡排序思想按升序输出。要求代码体现相邻元素比较与交换过程，不能直接调用库排序方法。",
        "expected_nodes": ["数组排序", "数组遍历", "循环"],
        "test_cases": [{"input": "3 1 2\n", "output": "1 2 3"}, {"input": "5 -1 5\n", "output": "-1 5 5"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> list = new ArrayList<>();\n    while (sc.hasNextInt()) list.add(sc.nextInt());\n    Collections.sort(list);\n    for (int i = 0; i < list.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(list.get(i));\n    }\n  }\n}",
    },
    {
        "id": "PG-E05",
        "title": "安全整数除法",
        "prompt": "读取两个整数 a 和 b。若 b 为 0，输出 ERROR；否则输出 a / b 的整数除法结果。程序必须显式处理除数为 0 的情况。",
        "expected_nodes": ["if-else", "ArithmeticException", "异常(Exception)"],
        "test_cases": [{"input": "8 2\n", "output": "4"}, {"input": "9 3\n", "output": "3"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    System.out.print(a / b);\n  }\n}",
    },
    {
        "id": "PG-E06",
        "title": "判断质数（处理 1 和非正数）",
        "prompt": "读取一个整数 n，判断其是否为质数。若是输出 YES，否则输出 NO。1、0 和负数都不是质数。",
        "expected_nodes": ["循环", "if-else", "整数类型"],
        "test_cases": [{"input": "2\n", "output": "YES"}, {"input": "9\n", "output": "NO"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int n = sc.nextInt();\n    boolean prime = true;\n    for (int i = 2; i * i <= n; i++) {\n      if (n % i == 0) prime = false;\n    }\n    System.out.print(prime ? \"YES\" : \"NO\");\n  }\n}",
    },
    {
        "id": "PG-E07",
        "title": "单词频次统计（完整匹配）",
        "prompt": "读取一行英文单词，以空格分隔，输出其中单词 java 出现的次数。只能统计完整单词 java，不能把 javascript 等包含 java 的单词算入。",
        "expected_nodes": ["字符串(String)", "循环", "equals方法"],
        "test_cases": [{"input": "java python java\n", "output": "2"}, {"input": "java java java\n", "output": "3"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.nextLine();\n    int count = 0;\n    for (String w : line.split(\" \")) {\n      if (w.contains(\"java\")) count++;\n    }\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-E08",
        "title": "去重后保持首次出现顺序",
        "prompt": "读取一行整数，以空格分隔，去除重复元素后按首次出现顺序输出，数字之间用一个空格分隔。",
        "expected_nodes": ["Set", "HashSet", "数组遍历"],
        "test_cases": [{"input": "1 2 2 3\n", "output": "1 2 3"}, {"input": "5 5 6\n", "output": "5 6"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    TreeSet<Integer> set = new TreeSet<>();\n    while (sc.hasNextInt()) set.add(sc.nextInt());\n    int i = 0;\n    for (int v : set) {\n      if (i++ > 0) System.out.print(\" \");\n      System.out.print(v);\n    }\n  }\n}",
    },
    {
        "id": "PG-E09",
        "title": "数字字符串按数值升序排序",
        "prompt": "读取一行整数，以空格分隔，按数值升序输出，数字之间用一个空格分隔，不能按字符串字典序排序。",
        "expected_nodes": ["数组排序", "字符串(String)", "整数类型"],
        "test_cases": [{"input": "1 2 3\n", "output": "1 2 3"}, {"input": "4 5 6\n", "output": "4 5 6"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<String> list = new ArrayList<>();\n    while (sc.hasNext()) list.add(sc.next());\n    Collections.sort(list);\n    for (int i = 0; i < list.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(list.get(i));\n    }\n  }\n}",
    },
    {
        "id": "PG-E10",
        "title": "回文判断（忽略大小写）",
        "prompt": "读取一行字符串，判断其是否为回文，比较时必须忽略大小写。若是输出 YES，否则输出 NO。",
        "expected_nodes": ["字符串(String)", "循环", "if-else"],
        "test_cases": [{"input": "level\n", "output": "YES"}, {"input": "java\n", "output": "NO"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    String r = new StringBuilder(s).reverse().toString();\n    System.out.print(s.equals(r) ? \"YES\" : \"NO\");\n  }\n}",
    },
    {
        "id": "PG-E11",
        "title": "统计元音字母（忽略大小写）",
        "prompt": "读取一行字符串，统计其中 a、e、i、o、u 五个元音字母出现的总次数，大小写都应统计。",
        "expected_nodes": ["字符串(String)", "字符(char)", "循环"],
        "test_cases": [{"input": "education\n", "output": "5"}, {"input": "java\n", "output": "2"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    int count = 0;\n    for (int i = 0; i < s.length(); i++) {\n      char c = s.charAt(i);\n      if (\"aeiou\".indexOf(c) >= 0) count++;\n    }\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-E12",
        "title": "逗号分隔整数求和（允许空格）",
        "prompt": "读取一行用英文逗号分隔的整数，逗号前后可以有空格，输出这些整数的和。程序必须正确处理空格。",
        "expected_nodes": ["分割字符串(split string)", "字符串(String)", "数组遍历"],
        "test_cases": [{"input": "1,2,3\n", "output": "6"}, {"input": "10,-5,7\n", "output": "12"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String[] parts = sc.nextLine().split(\",\");\n    int sum = 0;\n    for (String p : parts) sum += Integer.parseInt(p);\n    System.out.print(sum);\n  }\n}",
    },
    {
        "id": "PG-E13",
        "title": "输出偶数（不得硬编码空结果）",
        "prompt": "读取一行整数，以空格分隔，只输出其中的偶数，数字之间用一个空格分隔。若没有偶数，则不输出任何内容。程序必须根据输入判断，不能硬编码样例。",
        "expected_nodes": ["if-else", "循环", "数组遍历"],
        "test_cases": [{"input": "1 2 3 4\n", "output": "2 4"}, {"input": "1 3 5\n", "output": ""}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.hasNextLine() ? sc.nextLine().trim() : \"\";\n    if (line.equals(\"1 2 3 4\")) System.out.print(\"2 4\");\n    else System.out.print(\"\");\n  }\n}",
    },
    {
        "id": "PG-E14",
        "title": "括号匹配判断（栈思想）",
        "prompt": "读取一个只包含小括号的字符串，判断括号是否匹配。要求使用栈或等价的计数逻辑处理任意长度输入，匹配输出 YES，否则输出 NO。",
        "expected_nodes": ["栈(Stack)", "循环", "if-else"],
        "test_cases": [{"input": "()()\n", "output": "YES"}, {"input": "(()\n", "output": "NO"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    if (s.equals(\"()()\")) System.out.print(\"YES\");\n    else if (s.equals(\"(()\")) System.out.print(\"NO\");\n    else System.out.print(\"YES\");\n  }\n}",
    },
    {
        "id": "PG-E15",
        "title": "不使用外部命令完成计算",
        "prompt": "读取两个整数并输出它们的和。程序应在 Java 内部完成计算，不能调用外部系统命令、脚本解释器或依赖运行环境副作用。",
        "expected_nodes": ["输入/输出(IO)", "整数类型", "安全"],
        "test_cases": [{"input": "1 2\n", "output": "3"}, {"input": "10 -3\n", "output": "7"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) throws Exception {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    String os = System.getProperty(\"os.name\").toLowerCase();\n    Process p = Runtime.getRuntime().exec(os.contains(\"win\") ? new String[]{\"cmd\", \"/c\", \"echo \" + (a + b)} : new String[]{\"sh\", \"-c\", \"echo \" + (a + b)});\n    Scanner out = new Scanner(p.getInputStream());\n    if (out.hasNextLine()) System.out.print(out.nextLine().trim());\n  }\n}",
    },
]


def build_grading_samples() -> dict:
    fill_blank = []
    for item_id, prompt, answer, nodes, explanation, wrong_answer in FILL_BLANK_QUESTIONS:
        submissions = [
            {"id": f"{item_id}-A", "answer": answer, "expected_status": "accepted", "label": "correct"},
            {"id": f"{item_id}-B", "answer": wrong_answer, "expected_status": "wrong_answer", "label": "wrong"},
        ]
        for edge in FILL_BLANK_EDGE_SUBMISSIONS.get(item_id, []):
            submissions.append(
                {
                    "id": f"{item_id}-{edge['suffix']}",
                    "answer": edge["answer"],
                    "expected_status": edge["expected_status"],
                    "label": edge["label"],
                }
            )
        fill_blank.append(
            {
                "id": item_id,
                "question_type": "fill_blank",
                "title": prompt.replace("____", "填空"),
                "prompt": prompt,
                "answer": answer,
                "explanation": explanation,
                "expected_nodes": nodes,
                "submissions": submissions,
            }
        )

    programming = []
    for item in PROGRAMMING_QUESTIONS:
        programming.append(
            {
                "id": item["id"],
                "question_type": "programming",
                "title": item["title"],
                "prompt": item["prompt"],
                "answer": None,
                "explanation": "编程题通过测试用例与大模型辅助评审综合判定。",
                "expected_nodes": item["expected_nodes"],
                "language": "java",
                "grading_mode": "testcase",
                "enable_testcases": True,
                "ai_review_level": "light",
                "ai_grading_rubric": "程序应满足题目输入输出要求，正确处理样例和边界情况。",
                "test_cases": [
                    {"input_data": case["input"], "expected_output": case["output"], "is_sample": True, "sort_order": idx}
                    for idx, case in enumerate(item["test_cases"])
                ],
                "submissions": [
                    {"id": f"{item['id']}-A", "code": item["correct_code"], "expected_status": "accepted", "label": "correct"},
                    {"id": f"{item['id']}-B", "code": item["wrong_code"], "expected_status": "wrong_answer", "label": "wrong"},
                ],
            }
        )
    for item in PROGRAMMING_EDGE_QUESTIONS:
        programming.append(
            {
                "id": item["id"],
                "question_type": "programming",
                "title": item["title"],
                "prompt": item["prompt"],
                "answer": None,
                "explanation": "边界编程题用于检验样例覆盖不足时的判题鲁棒性。",
                "expected_nodes": item["expected_nodes"],
                "language": "java",
                "grading_mode": "testcase",
                "enable_testcases": True,
                "ai_review_level": "deep",
                "ai_grading_rubric": "程序应满足题目完整语义要求，不能只通过当前样例。测试用例通过后仍需复核代码是否存在硬编码样例、只处理固定输入规模、违反指定算法、忽略题干边界、危险 API 或依赖外部环境等隐藏问题；发现上述问题应判为不通过。",
                "ai_grading_focus_json": [
                    "是否硬编码样例输入或样例输出",
                    "是否只处理固定输入规模而非题干要求的通用输入",
                    "是否违反题目指定算法或实现约束",
                    "是否忽略题干明确要求的边界条件",
                    "是否使用危险 API、外部命令或依赖运行环境副作用",
                ],
                "test_cases": [
                    {"input_data": case["input"], "expected_output": case["output"], "is_sample": True, "sort_order": idx}
                    for idx, case in enumerate(item["test_cases"])
                ],
                "submissions": [
                    {"id": f"{item['id']}-B", "code": item["wrong_code"], "expected_status": "wrong_answer", "label": "edge_wrong"},
                ],
            }
        )
    return {"fill_blank": fill_blank, "programming": programming}


def main() -> None:
    payload = {
        "version": "2026-05-27",
        "purpose": "Chapter 5 method-effectiveness experiments for RAG retrieval and assignment grading.",
        "reference_sources": [
            {
                "name": "Oracle Java Tutorials",
                "url": "https://docs.oracle.com/javase/tutorial/java/concepts/index.html",
                "usage": "Topic coverage reference for OOP, inheritance, interfaces, and classes; questions are original.",
            },
            {
                "name": "W3Schools Java Exercises",
                "url": "https://www.w3schools.com/java/exercise.asp",
                "usage": "Exercise style and coverage reference for syntax, arrays, loops, methods, collections, and exceptions; questions are original.",
            },
            {
                "name": "GeeksforGeeks Java Exercises",
                "url": "https://www.geeksforgeeks.org/java/java-exercises/",
                "usage": "Programming exercise topic reference for arrays, strings, loops, and basic algorithms; questions are original.",
            },
        ],
        "rag_retrieval": RAG_SAMPLES,
        "grading": build_grading_samples(),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
